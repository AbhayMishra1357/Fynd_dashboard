# ai_sentiment_reply.py
"""
AI module: sentiment-based reply generator for review system.

- Tries to load a saved sentiment pipeline at models/sentiment_pipe.joblib
- If not found, trains a small deterministic pipeline from a bootstrap review dataset
  (review-based sentences mapped to sentiment labels).
- Exposes generate_reply(review, rating=None) -> dict
  which returns reply, summary, sentiment, recommendations, model_info.

Design goals:
- Deterministic, small-footprint (suitable for Render free tier).
- No heavy DL libraries, no external downloads required.
- Avoid hallucination: replies built from templates + short summary + deterministic recs.
"""

import os
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib

# CONFIG
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
SENT_MODEL_PATH = MODEL_DIR / "sentiment_pipe.joblib"

# Ensure model dir exists
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Bootstrapped labeled reviews for training (small, review-based, deterministic).
# These are intentionally conservative and cover common review patterns.
_BOOTSTRAP_TRAIN = [
    # Positive
    ("Love the new UI, very smooth and fast", "positive"),
    ("Excellent app — works perfectly", "positive"),
    ("Very satisfied, 5 stars", "positive"),
    ("Great experience, thank you!", "positive"),
    ("Nice feature set and great support", "positive"),

    # Neutral
    ("It's okay, does the job", "neutral"),
    ("Average performance and UI", "neutral"),
    ("Not bad, but could be improved", "neutral"),
    ("Three stars, acceptable", "neutral"),
    ("Works as advertised", "neutral"),

    # Negative
    ("App crashes on save and I lost my work", "negative"),
    ("Very slow and unusable", "negative"),
    ("Terrible experience, frequent errors", "negative"),
    ("I am disappointed, not working", "negative"),
    ("Two stars — lots of bugs and freezes", "negative"),
]

# Template replies per sentiment (concise + deterministic)
_TEMPLATES = {
    "positive": "Thanks for the positive feedback! We're delighted to hear that. Summary: {summary}",
    "neutral": "Thanks for the feedback. Summary: {summary}. We'll consider improvements.",
    "negative": "Sorry for the trouble — we appreciate this feedback. Summary: {summary}. Next steps: {recs}"
}

# Recommendation map by sentiment (short, actionable)
_RECOMMENDATIONS = {
    "positive": ["Share with product team", "Thank user"],
    "neutral": ["Log for product review", "Monitor feedback trend"],
    "negative": ["Escalate to engineering", "Request logs/screenshots", "Offer support contact"]
}


def _simple_normalize(text: str) -> str:
    # Lowercase, strip, collapse whitespace
    if not isinstance(text, str):
        return ""
    t = text.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _simple_summarize(text: str, max_sentences: int = 1) -> str:
    # Very light-weight extractive summary: pick the sentence with the most "content" words
    if not text or not isinstance(text, str):
        return ""
    # split into sentences by punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= max_sentences:
        return text.strip()
    # score sentences by number of words (simple heuristic)
    scored = [(len(re.findall(r'\w+', s)), i, s.strip()) for i, s in enumerate(sentences) if s.strip()]
    if not scored:
        return text.strip()
    scored.sort(reverse=True)  # highest word count first
    selected = [s for (_, _, s) in scored[:max_sentences]]
    # preserve original order
    selected_set = set(selected)
    ordered = [s for s in sentences if s.strip() in selected_set]
    return " ".join([s.strip() for s in ordered])


def _map_rating_to_sentiment(rating: Optional[int]) -> Optional[str]:
    if rating is None:
        return None
    try:
        r = int(rating)
    except Exception:
        return None
    if r >= 4:
        return "positive"
    if r == 3:
        return "neutral"
    return "negative"


class SentimentModel:
    """
    Wrapper for sentiment pipeline. Loads if saved, otherwise trains on bootstrap data.
    """
    def __init__(self, model_path: Path = SENT_MODEL_PATH):
        self.model_path = model_path
        self.pipeline: Pipeline = None
        self.model_info: Dict[str, Any] = {"loaded_from": None}
        self._ensure_model()

    def _ensure_model(self):
        if self.model_path.exists():
            try:
                self.pipeline = joblib.load(str(self.model_path))
                self.model_info = {"loaded_from": str(self.model_path), "trained": False}
                return
            except Exception:
                # If loading fails, fall through to retrain
                pass
        # Train from bootstrap
        texts = [t for (t, label) in _BOOTSTRAP_TRAIN]
        labels = [label for (t, label) in _BOOTSTRAP_TRAIN]
        # Using TF-IDF + Logistic Regression (small, deterministic)
        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=2000)),
            ("clf", LogisticRegression(max_iter=500, class_weight="balanced", solver="liblinear"))
        ])
        pipe.fit(texts, labels)
        # Save
        try:
            joblib.dump(pipe, str(self.model_path))
            self.model_info = {"loaded_from": str(self.model_path), "trained": True, "bootstrap_size": len(texts)}
        except Exception as e:
            # couldn't save, but still keep in-memory model
            self.model_info = {"loaded_from": None, "trained": True, "bootstrap_size": len(texts), "save_error": str(e)}
        self.pipeline = pipe

    def predict(self, text: str) -> str:
        if not self.pipeline:
            self._ensure_model()
        text_norm = _simple_normalize(text)
        pred = self.pipeline.predict([text_norm])[0]
        # normalize to expected labels if needed
        if pred not in ("positive", "neutral", "negative"):
            # fallback mapping
            return _map_rating_to_sentiment(None) or "neutral"
        return pred


# Instantiate (loads or trains)
_SENT_MODEL = SentimentModel()


def generate_reply(review: str, rating: Optional[int] = None) -> Dict[str, Any]:
    """
    Main function to call from your Flask app.
    Args:
      review: user review text
      rating: optional integer rating (1-5). If provided, rating will be used as trusted source for sentiment mapping.
    Returns:
      dict with keys: reply, summary, sentiment, recommendations (list), model_info
    """
    if not isinstance(review, str):
        review = str(review or "")

    # Summarize first (short)
    summary = _simple_summarize(review, max_sentences=1)

    # Determine sentiment: prefer rating mapping if rating provided (more reliable)
    sentiment_from_rating = _map_rating_to_sentiment(rating)
    if sentiment_from_rating:
        sentiment = sentiment_from_rating
        used = "rating"
    else:
        # predict from text
        sentiment = _SENT_MODEL.predict(review)
        used = "model"

    # Recommendations & reply template
    recs = _RECOMMENDATIONS.get(sentiment, ["Log for review"])
    template = _TEMPLATES.get(sentiment, _TEMPLATES["neutral"])
    reply = template.format(summary=summary, recs="; ".join(recs))

    # Build result
    result = {
        "reply": reply,
        "summary": summary,
        "sentiment": sentiment,
        "recommendations": recs,
        "model_info": {
            "sentiment_source": used,
            "model_path": str(_SENT_MODEL.model_path) if _SENT_MODEL.model_path else None,
            **_SENT_MODEL.model_info
        }
    }
    return result


# Convenience small test runner when executed directly
if __name__ == "__main__":
    # quick demo
    examples = [
        ("App crashes on save, lost data", 1),
        ("Nice and fast, good job", 5),
        ("It's okay, could be improved", 3),
        ("The feature is missing export option", None)
    ]
    for text, r in examples:
        out = generate_reply(text, r)
        print("---")
        print("Review:", text)
        print("Rating:", r)
        print("Sentiment:", out["sentiment"])
        print("Summary:", out["summary"])
        print("Reply:", out["reply"])
        print("Model info:", out["model_info"])
