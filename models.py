# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Submission(db.Model):
    __tablename__ = "submissions"
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    review = db.Column(db.Text, nullable=False)
    ai_reply = db.Column(db.Text)
    ai_summary = db.Column(db.Text)
    ai_recommendations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "rating": self.rating,
            "review": self.review,
            "ai_reply": self.ai_reply,
            "ai_summary": self.ai_summary,
            "ai_recommendations": self.ai_recommendations,
            "created_at": self.created_at.isoformat()
        }
