"""
Trillium V2 — Project Manager
Gestione multi-progetto: salva/carica/elimina configurazioni di parametri.
Ogni progetto ha: nome, parametri, data creazione, data ultima modifica.
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_PROJECTS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "projects.json"
)

MAX_PROJECTS = 50


def save_project(name: str, params: dict) -> bool:
    """Salva un progetto con i parametri correnti."""
    try:
        projects = _load_raw()
        now = datetime.now().isoformat()

        # Cerca esistente per aggiornare
        existing = next((p for p in projects if p["name"] == name), None)
        if existing:
            existing["params"] = params
            existing["updated_at"] = now
            existing["revision"] = existing.get("revision", 0) + 1
        else:
            projects.append({
                "name": name,
                "params": params,
                "created_at": now,
                "updated_at": now,
                "revision": 1,
            })

        # Limita dimensione
        if len(projects) > MAX_PROJECTS:
            projects = projects[-MAX_PROJECTS:]

        _save_raw(projects)
        logger.info(f"Progetto '{name}' salvato ({len(projects)} totali)")
        return True

    except Exception as e:
        logger.warning(f"Errore salvataggio progetto: {e}")
        return False


def load_project(name: str) -> dict | None:
    """Carica i parametri di un progetto."""
    projects = _load_raw()
    proj = next((p for p in projects if p["name"] == name), None)
    return proj["params"] if proj else None


def list_projects() -> list[dict]:
    """Lista tutti i progetti salvati (nome, data, famiglia, materiale)."""
    projects = _load_raw()
    result = []
    for p in projects:
        params = p.get("params", {})
        result.append({
            "name": p["name"],
            "family": params.get("pump_family", "—"),
            "material": params.get("material", "—"),
            "revision": p.get("revision", 1),
            "created_at": p.get("created_at", ""),
            "updated_at": p.get("updated_at", ""),
        })
    return sorted(result, key=lambda x: x.get("updated_at", ""), reverse=True)


def delete_project(name: str) -> bool:
    """Elimina un progetto."""
    try:
        projects = _load_raw()
        projects = [p for p in projects if p["name"] != name]
        _save_raw(projects)
        logger.info(f"Progetto '{name}' eliminato")
        return True
    except Exception as e:
        logger.warning(f"Errore eliminazione progetto: {e}")
        return False


def _load_raw() -> list:
    """Carica il file JSON grezzo."""
    if not os.path.exists(_PROJECTS_FILE):
        return []
    try:
        with open(_PROJECTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_raw(data: list):
    """Salva il file JSON."""
    with open(_PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
