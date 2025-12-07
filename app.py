 @app.route("/", methods=["GET", "POST"])
    def user_dashboard():

      from sqlalchemy import text
      # quick test query
      result = db.session.execute(text("SELECT 1")).scalar()
      return {
            "status": "ok",
            "message": "Database connected successfully",
            "result": result,
            "db_url": app.config["SQLALCHEMY_DATABASE_URI"],  
        }, 200

    # if request.method == "POST":
    #     try:
    #         rating = int(request.form.get("rating", 5))
    #     except Exception:
    #         rating = 5
    #     review = request.form.get("review", "").strip()
    #     if not review:
    #         return render_template("user.html", error="Please write a review.", saved=False)

    #     # --- Use sentiment-based module to generate reply/summary/recommendations ---
    #     try:
    #         result = generate_sentiment_reply(review, rating)
    #         # Expecting result keys: reply, summary, recommendations (list), sentiment, model_info
    #         ai_reply = result.get("reply", "").strip()
    #         ai_summary = result.get("summary", "").strip()
    #         recs = result.get("recommendations", [])
    #         # store recommendations as a semicolon separated string for DB column
    #         ai_recs = "; ".join(recs) if isinstance(recs, (list, tuple)) else str(recs)
    #     except Exception as e:
    #         # Fail-safe: if sentiment module errors, fallback to simple templated reply
    #         app.logger.exception("Sentiment module error, falling back to default reply: %s", e)
    #         ai_reply = "Thanks for your review. We have received your feedback."
    #         ai_summary = review[:200]
    #         ai_recs = "Log for review"

    #     s = Submission(
    #         rating=rating,
    #         review=review,
    #         ai_reply=ai_reply,
    #         ai_summary=ai_summary,
    #         ai_recommendations=ai_recs,
    #     )
    #     db.session.add(s)
    #     db.session.commit()
    #     return render_template("user.html", saved=True, reply=ai_reply, summary=ai_summary)

    # return render_template("user.html", saved=False)

    # ----- basic auth for admin (kept for optional use) -----
    # read and normalize admin creds once, trim whitespace
    ADMIN_USER_ENV = os.getenv("ADMIN_USER")
    ADMIN_PASS_ENV = os.getenv("ADMIN_PASS")

    # Log presence (do not log actual password content)
    app.logger.info("ADMIN_USER present: %s", bool(ADMIN_USER_ENV))
    app.logger.info("ADMIN_PASS present: %s (length=%s)", bool(ADMIN_PASS_ENV),
                    len(ADMIN_PASS_ENV) if ADMIN_PASS_ENV else 0)

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

    @app.route("/db-test")
    def db_test():
        try:
            from sqlalchemy import text
            # quick test query
            result = db.session.execute(text("SELECT 1")).scalar()
            return {
                "status": "ok",
                "message": "Database connected successfully",
                "result": result,
                "db_url": app.config["SQLALCHEMY_DATABASE_URI"],
            }, 200
        except Exception as e:
            app.logger.exception("DB test failed")
            return {
                "status": "error",
                "message": "Database connection failed",
                "error": str(e),
                "db_url": app.config["SQLALCHEMY_DATABASE_URI"],
            }, 500


# Allow "python app.py" to run dev server
if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
