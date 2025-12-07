import os
import logging
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv
from flask_migrate import Migrate

# load .env (if present)
load_dotenv()

# import models
from models import db, Submission

# Import the sentiment-based reply generator (sentiments.py must expose generate_reply)
# Example: from sentiments import generate_reply
from ai_sentiment_reply import generate_reply as generate_sentiment_reply

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # -------------------------
    # DATABASE: safe normalization
    # -------------------------
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    if not DATABASE_URL:
        # local fallback to sqlite for dev if DATABASE_URL not provided
        DATABASE_URL = "sqlite:///./data/app.db"

    # Normalize Render's 'postgres://' to SQLAlchemy-friendly 'postgresql://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # If using sqlite, ensure parent directory exists and convert to absolute path
    if DATABASE_URL.startswith("sqlite:///"):
        # remove prefix and get file path
        sqlite_path = DATABASE_URL.replace("sqlite:///", "", 1)

        # If path not absolute, make it absolute relative to project cwd
        if not os.path.isabs(sqlite_path):
            sqlite_path = os.path.abspath(os.path.join(os.getcwd(), sqlite_path))

        # Ensure parent directory exists
        parent = os.path.dirname(sqlite_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        # Rebuild full URL
        DATABASE_URL = "sqlite:///" + sqlite_path

    # Set SQLAlchemy config
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # engine pool options (tunable via env)
    try:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": int(os.getenv("DB_POOL_SIZE", 5)),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 5)),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", 30)),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", 1800)),
        }
    except Exception:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}

    # -------------------------
    # Logging
    # -------------------------
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.info("SQLALCHEMY_DATABASE_URI = %s", app.config["SQLALCHEMY_DATABASE_URI"])

    # -------------------------
    # Initialize DB + migrations
    # -------------------------
    db.init_app(app)
    migrate = Migrate(app, db)

    # OPTIONAL: create tables automatically in dev if env var set
    if os.getenv("FORCE_DB_CREATE", "0") == "1":
        with app.app_context():
            app.logger.info("FORCE_DB_CREATE=1 -> running db.create_all()")
            db.create_all()

    # ---------- routes ----------
    @app.route("/", methods=["GET", "POST"])
    def user_dashboard():
        if request.method == "POST":
            try:
                rating = int(request.form.get("rating", 5))
            except Exception:
                rating = 5
            review = request.form.get("review", "").strip()
            if not review:
                return render_template("user.html", error="Please write a review.", saved=False)

            # --- Use sentiment-based module to generate reply/summary/recommendations ---
            try:
                result = generate_sentiment_reply(review, rating)
                # Expecting result keys: reply, summary, recommendations (list), sentiment, model_info
                ai_reply = result.get("reply", "").strip()
                ai_summary = result.get("summary", "").strip()
                recs = result.get("recommendations", [])
                # store recommendations as a semicolon separated string for DB column
                ai_recs = "; ".join(recs) if isinstance(recs, (list, tuple)) else str(recs)
            except Exception as e:
                # Fail-safe: if sentiment module errors, fallback to simple templated reply
                app.logger.exception("Sentiment module error, falling back to default reply: %s", e)
                ai_reply = "Thanks for your review. We have received your feedback."
                ai_summary = review[:200]
                ai_recs = "Log for review"

            s = Submission(
                rating=rating,
                review=review,
                ai_reply=ai_reply,
                ai_summary=ai_summary,
                ai_recommendations=ai_recs,
            )
            db.session.add(s)
            db.session.commit()
            return render_template("user.html", saved=True, reply=ai_reply, summary=ai_summary)

        return render_template("user.html", saved=False)

    # ----- basic auth for admin (kept for optional use) -----
    # read and normalize admin creds once, trim whitespace
    ADMIN_USER_ENV = os.getenv("ADMIN_USER")
    ADMIN_PASS_ENV = os.getenv("ADMIN_PASS")

    # Log presence (do not log actual password content)
    app.logger.info("ADMIN_USER present: %s", bool(ADMIN_USER_ENV))
    app.logger.info("ADMIN_PASS present: %s (length=%s)", bool(ADMIN_PASS_ENV), len(ADMIN_PASS_ENV) if ADMIN_PASS_ENV else 0)

    def check_auth(username, password):
        expected_user = (ADMIN_USER_ENV or "").strip()
        expected_pass = (ADMIN_PASS_ENV or "").strip()

        # Development-friendly defaults if env missing (ONLY for local dev)
        # Set DEV_ALLOW_DEFAULT_CREDS=0 to disable defaults
        if os.getenv("DEV_ALLOW_DEFAULT_CREDS", "1") == "1":
            if not expected_user:
                expected_user = "admin"
            if not expected_pass:
                expected_pass = "changeme"

        return (username == expected_user) and (password == expected_pass)

    def authenticate():
        return Response('Login required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth:
                app.logger.debug("No auth header received for admin route.")
                return authenticate()
            app.logger.debug("Auth provided for user=%s", auth.username)
            if not check_auth(auth.username, auth.password):
                app.logger.warning("Auth failed for user=%s", auth.username)
                return authenticate()
            return f(*args, **kwargs)
        return decorated

    @app.route("/admin")
    # If you want to enable basic-auth again, uncomment the decorator:
    # @requires_auth
    def admin_dashboard():
        subs = Submission.query.order_by(Submission.created_at.desc()).limit(200).all()
        total = len(subs)
        avg = round((sum((s.rating for s in subs), 0) / total), 2) if total else 0.0
        return render_template("admin.html", submissions=subs, total=total, avg=avg)

    @app.route("/api/latest")
    def api_latest():
        subs = Submission.query.order_by(Submission.created_at.desc()).limit(50).all()
        return jsonify([s.to_dict() for s in subs])

    @app.route("/healthz")
    def healthz():
        # basic health check; you can extend to run a DB test query if desired
        return jsonify({"status": "ok", "db": "configured"}), 200

    return app


# Allow "python app.py" to run dev server
if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
