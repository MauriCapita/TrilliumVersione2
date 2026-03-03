"""
Trillium V2 — Reference Weights
Database pesi reali delle pompe costruite. L'utente inserisce pesi misurati
che vengono usati come riferimento per validare le stime future.
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_REF_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "reference_weights.json"
)

MAX_REFERENCES = 200


def add_reference(pump_name: str, family: str, total_weight_kg: float,
                  components: dict = None, notes: str = "") -> bool:
    """Aggiunge un peso reale di riferimento."""
    try:
        refs = _load_raw()
        now = datetime.now().isoformat()

        # Cerca duplicato
        existing = next((r for r in refs if r["pump_name"] == pump_name), None)
        if existing:
            existing["family"] = family
            existing["total_weight_kg"] = total_weight_kg
            existing["components"] = components or {}
            existing["notes"] = notes
            existing["updated_at"] = now
        else:
            refs.append({
                "pump_name": pump_name,
                "family": family,
                "total_weight_kg": total_weight_kg,
                "components": components or {},
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            })

        if len(refs) > MAX_REFERENCES:
            refs = refs[-MAX_REFERENCES:]

        _save_raw(refs)
        logger.info(f"Riferimento '{pump_name}' salvato ({len(refs)} totali)")
        return True

    except Exception as e:
        logger.warning(f"Errore salvataggio riferimento: {e}")
        return False


def get_references(family: str = None) -> list[dict]:
    """Lista riferimenti, opzionalmente filtrati per famiglia."""
    refs = _load_raw()
    if family:
        refs = [r for r in refs if r.get("family", "").upper() == family.upper()]
    return sorted(refs, key=lambda x: x.get("updated_at", ""), reverse=True)


def delete_reference(pump_name: str) -> bool:
    """Elimina un riferimento."""
    try:
        refs = _load_raw()
        refs = [r for r in refs if r["pump_name"] != pump_name]
        _save_raw(refs)
        return True
    except Exception:
        return False


def find_similar(params: dict, top_k: int = 3) -> list[dict]:
    """Trova i riferimenti più simili ai parametri dati.
    Similarity basata su: stessa famiglia > peso simile.
    """
    refs = _load_raw()
    if not refs:
        return []

    family = params.get("pump_family", "")
    scored = []

    for ref in refs:
        score = 0
        # Stessa famiglia = alta similarità
        if ref.get("family", "").upper() == family.upper():
            score += 100

        # Famiglia simile (stessa lettera base: BB1 ~ BB2)
        elif (ref.get("family", "")[:2].upper() == family[:2].upper() if family else False):
            score += 50

        scored.append((score, ref))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [ref for score, ref in scored[:top_k] if score > 0]


def _load_raw() -> list:
    if not os.path.exists(_REF_FILE):
        return []
    try:
        with open(_REF_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_raw(data: list):
    with open(_REF_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
