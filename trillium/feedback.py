"""
Trillium RAG - Sistema Feedback
Salva valutazioni (like/dislike) sulle risposte e domande suggerite.
Persistenza su file JSON locale.
"""

import json
import os
import time
from typing import Optional

_FEEDBACK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback_data.json")


def _load_feedback() -> list:
    if not os.path.exists(_FEEDBACK_FILE):
        return []
    try:
        with open(_FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_feedback(data: list):
    with open(_FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_rating(question: str, answer: str, rating: str, comment: str = ""):
    """
    Salva un feedback. rating = 'positive' o 'negative'.
    """
    data = _load_feedback()
    data.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question[:500],
        "answer_preview": answer[:300],
        "rating": rating,
        "comment": comment,
    })
    _save_feedback(data)


def get_feedback_stats() -> dict:
    """Restituisce statistiche aggregate sui feedback."""
    data = _load_feedback()
    total = len(data)
    positive = sum(1 for d in data if d.get("rating") == "positive")
    negative = sum(1 for d in data if d.get("rating") == "negative")
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "satisfaction_rate": (positive / total * 100) if total > 0 else 0,
    }


def get_recent_negative_feedback(limit: int = 10) -> list:
    """Restituisce gli ultimi feedback negativi per analisi."""
    data = _load_feedback()
    negatives = [d for d in data if d.get("rating") == "negative"]
    return negatives[-limit:]


def generate_suggested_questions(question: str, answer: str) -> list:
    """
    Genera 3 domande di follow-up basate sulla domanda e risposta corrente.
    Usa GPT-4o-mini per velocità e costo ridotto.
    """
    from config import OPENAI_API_KEY
    if not OPENAI_API_KEY:
        return []

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Genera esattamente 3 domande di follow-up brevi e pertinenti, "
                        "in italiano, basate sulla domanda e risposta dell'utente. "
                        "Le domande devono essere utili per approfondire l'argomento "
                        "nel contesto di documentazione tecnica su pompe centrifughe "
                        "(SOP, Mod Excel, normative API/ASME). "
                        "Restituisci SOLO le 3 domande, una per riga, senza numeri o bullet."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Domanda: {question[:200]}\n\nRisposta: {answer[:500]}",
                },
            ],
            temperature=0.7,
            max_tokens=200,
        )

        text = response.choices[0].message.content.strip()
        questions = [q.strip().lstrip("0123456789.-) ") for q in text.split("\n") if q.strip()]
        return questions[:3]

    except Exception:
        return []
