"""
Trillium V2 — Estimation History
Persistenza stime per analytics, storico, e trend.
Salva e carica stime da file JSON locale.
Supporta versioning: ogni stima può avere un project_name e incremento automatico revisione.
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "estimation_history.json"
)

MAX_HISTORY = 500  # Aumentato per supportare versioning


def save_estimation(result, project_name: str = None) -> bool:
    """Salva una stima completata nello storico con dettagli completi."""
    try:
        history = _load_raw()

        # Calcola revisione per il progetto
        revision = 1
        if project_name:
            existing = [e for e in history if e.get("project_name") == project_name]
            revision = len(existing) + 1

        # Salva componenti completi
        components_detail = []
        for c in result.components:
            if c.is_estimated:
                components_detail.append({
                    "name": c.component_name,
                    "group": c.group,
                    "weight_kg": round(c.estimated_weight_kg, 2) if c.estimated_weight_kg else 0,
                    "confidence": c.confidence,
                    "method": c.estimation_method or "",
                })

        entry = {
            "job_id": result.job_id,
            "timestamp": result.timestamp.isoformat(),
            "project_name": project_name or "",
            "revision": revision,
            # Parametri completi
            "params": {
                "pump_family": result.params.get("pump_family", ""),
                "nq": result.params.get("nq", 0),
                "scale_factor": result.params.get("scale_factor", 1.0),
                "num_stages": result.params.get("num_stages", 1),
                "pressure": result.params.get("pressure", 0),
                "temperature": result.params.get("temperature", 0),
                "material": result.params.get("material", ""),
                "wall_thickness": result.params.get("wall_thickness", 0),
                "flange_rating": result.params.get("flange_rating", 150),
                "suction_size": result.params.get("suction_size", 8),
                "discharge_size": result.params.get("discharge_size", 6),
            },
            # Riepilogo (per compatibilità con analytics)
            "pump_family": result.params.get("pump_family", ""),
            "nq": result.params.get("nq", 0),
            "scale_factor": result.params.get("scale_factor", 1.0),
            "pressure": result.params.get("pressure", 0),
            "temperature": result.params.get("temperature", 0),
            "material": result.params.get("material", ""),
            "flange_rating": result.params.get("flange_rating", 150),
            "total_weight_kg": round(result.total_weight_kg, 1),
            "components_estimated": len([c for c in result.components if c.is_estimated]),
            "components_total": len(result.components),
            "high_confidence": len([c for c in result.components if c.confidence == "alta"]),
            "warnings": len(result.warnings),
            # Dettagli componenti
            "components_detail": components_detail,
        }

        history.append(entry)

        # Limita dimensione
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        logger.info(f"Stima {result.job_id} salvata nello storico ({len(history)} totali)")
        return True

    except Exception as e:
        logger.warning(f"Errore salvataggio storico: {e}")
        return False


def get_estimation(job_id: str) -> dict | None:
    """Carica una singola stima per job_id."""
    history = _load_raw()
    return next((e for e in history if e.get("job_id") == job_id), None)


def get_revisions(project_name: str) -> list[dict]:
    """Tutte le revisioni di un progetto, ordinate per revision number."""
    history = _load_raw()
    revisions = [e for e in history if e.get("project_name") == project_name]
    return sorted(revisions, key=lambda x: x.get("revision", 0))


def get_history() -> list[dict]:
    """Restituisce lo storico completo delle stime."""
    return _load_raw()


def get_stats() -> dict:
    """Statistiche aggregate sullo storico."""
    history = _load_raw()
    if not history:
        return {"total": 0}

    families = {}
    materials = {}
    weights = []
    conf_totals = []

    for entry in history:
        fam = entry.get("pump_family", "")
        mat = entry.get("material", "")
        families[fam] = families.get(fam, 0) + 1
        materials[mat] = materials.get(mat, 0) + 1
        weights.append(entry.get("total_weight_kg", 0))
        total = entry.get("components_total", 1)
        high = entry.get("high_confidence", 0)
        if total > 0:
            conf_totals.append(high / total * 100)

    return {
        "total": len(history),
        "families": families,
        "materials": materials,
        "avg_weight": sum(weights) / len(weights) if weights else 0,
        "max_weight": max(weights) if weights else 0,
        "min_weight": min(weights) if weights else 0,
        "avg_confidence_pct": sum(conf_totals) / len(conf_totals) if conf_totals else 0,
        "recent": history[-5:][::-1],
    }


def _load_raw() -> list:
    """Carica il file JSON grezzo."""
    if not os.path.exists(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []
