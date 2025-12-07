# llm.py
import os
import requests

# Replace this with a real OpenAI or other LLM integration.
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

def call_llm_for_reply(review: str, rating: int):
    """
    Return tuple: (reply, summary, recommendations)
    If OPENAI_API_KEY is not set, return deterministic local values (useful for dev).
    """
    if not OPENAI_KEY:
        reply = f"Thanks for your {rating}-star review! We appreciate the feedback."
        summary = review[:200] + ("..." if len(review) > 200 else "")
        recs = "1) Acknowledge user; 2) Escalate if rating <=2; 3) Add to improvement backlog."
        return reply, summary, recs

    # Example OpenAI call skeleton — uncomment and adjust if you want to enable
    # headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    # data = {
    #     "model": "gpt-4o-mini",
    #     "messages": [{"role": "system", "content": "You are concise and helpful."},
    #                  {"role": "user", "content": f"Review: {review}\nRating: {rating}"}],
    #     "max_tokens": 150
    # }
    # r = requests.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers, timeout=20)
    # text = r.json()["choices"][0]["message"]["content"].strip()
    # For simplicity here we split text into three parts — but production should ask three prompts
    # return text, text, text
    return "LLM reply placeholder", "LLM summary placeholder", "LLM recommendations placeholder"
