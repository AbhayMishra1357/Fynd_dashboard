from flask import Flask, request, render_template, jsonify, Response
from functools import wraps
from sqlalchemy import text
from models import db, Submission
import os


def create_app():
    app = Flask(__name__)

    # Database config already set in your environment
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # ---------------------- USER ROUTE ----------------------
    @app.route("/", methods=["GET", "POST"])
    def user_dashboard():
        # DB quick test
        try:
            result = db.session.execute(text("SELECT 1")).scalar()
        except Exception:
            return {"status": "error", "message": "Database connection failed"}, 500

        # GET only
        if request.method == "GET":
            return {
                "status": "ok",
                "message": "Database connected successfully",
                "result": result,
                "db_url": app.config["SQLALCHEMY_DATABASE_URI"]
            }, 200

        # POST logic (commented for now)
        # --- your code for sentiment and saving review goes here ---
        return render_template("user.html", saved=False)

    # ---------------------- ADMIN BASIC AUTH ----------------------
    ADMIN_USER_ENV = os.getenv("ADMIN_USER")
    ADMIN_PASS_ENV = os.getenv("ADMIN_PASS")

    def check_auth(username, password):
        expected_user = (ADMIN_USER_ENV or "admin").strip()
        expected_pass = (ADMIN_PASS_ENV or "changeme").strip()
        return username == expected_user and password == expected_pass

    def authenticate():
        return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})

    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
            return f(*args, **kwargs)
        return decorated

    # ---------------------- ADMIN PAGE ----------------------
    @app.route("/admin")
    # @requires_auth   # uncomment if you want login protection
    def admin_dashboard():
        subs = Submission.query.order_by(Submission.created_at.desc()).limit(200).all()
        total = len(subs)
        avg = round(sum(s.rating for s in subs) / total, 2) if total else 0.0
        return render_template("admin.html", submissions=subs, total=total, avg=avg)

    # ---------------------- API: Latest Submissions ----------------------
    @app.route("/api/latest")
    def api_latest():
        subs = Submission.query.order_by(Submission.created_at.desc()).limit(50).all()
        return jsonify([s.to_dict() for s in subs])

    # ---------------------- HEALTH CHECK ----------------------
    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok", "db": "configured"}), 200

    # ---------------------- DATABASE TEST ----------------------
    @app.route("/db-test")
    def db_test():
        try:
            result = db.session.execute(text("SELECT 1")).scalar()
            return {
                "status": "ok",
                "message": "Database connected successfully",
                "result": result,
                "db_url": app.config["SQLALCHEMY_DATABASE_URI"]
            }, 200
        except Exception as e:
            return {
                "status": "error",
                "message": "Database connection failed",
                "error": str(e),
                "db_url": app.config["SQLALCHEMY_DATABASE_URI"]
            }, 500

    return app


# ---------------------- Dev Mode Entry ----------------------
if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
