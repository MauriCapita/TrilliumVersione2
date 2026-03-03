"""
Trillium V2 — Pump Database
Database JSON locale per pompe estratte automaticamente dai disegni.
Permette ricerca, filtro, statistiche, e ricostruzione da Qdrant.
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_DB_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "pump_database.json"
)

MAX_ENTRIES = 5000


# ============================================================
# CRUD
# ============================================================

def save_pump_data(data: dict) -> bool:
    """Salva dati pompa nella tabella. Aggiorna se source gia presente."""
    try:
        db = _load_raw()
        source = data.get("source", "")

        # Aggiorna se gia presente
        for i, entry in enumerate(db):
            if entry.get("source") == source:
                data["updated_at"] = datetime.now().isoformat()
                db[i] = data
                _save_raw(db)
                return True

        # Nuovo inserimento
        data["created_at"] = datetime.now().isoformat()
        data["updated_at"] = data["created_at"]
        db.append(data)

        # Limita dimensione
        if len(db) > MAX_ENTRIES:
            db = db[-MAX_ENTRIES:]

        _save_raw(db)
        return True

    except Exception as e:
        logger.warning(f"Errore salvataggio pump data: {e}")
        return False


def get_all_pumps() -> list[dict]:
    """Restituisce tutto il database pompe."""
    return _load_raw()


def get_pumps_by_family(family: str) -> list[dict]:
    """Filtra pompe per famiglia (OH2, BB1, VS4, etc.)."""
    db = _load_raw()
    family_upper = family.upper()
    return [p for p in db if p.get("pump_family", "").upper() == family_upper]


def get_pumps_by_component(component_type: str) -> list[dict]:
    """Filtra pompe per tipo componente (casing, impeller, shaft, etc.)."""
    db = _load_raw()
    return [p for p in db if p.get("component_type", "") == component_type]


def get_pumps_with_weight() -> list[dict]:
    """Restituisce solo pompe con peso estratto."""
    db = _load_raw()
    return [p for p in db if p.get("weight_kg") is not None and p["weight_kg"] > 0]


def search_pumps(query: dict) -> list[dict]:
    """Cerca pompe che matchano i criteri.

    Args:
        query: Dict con chiavi opzionali:
            - pump_family: str (es. "OH2")
            - component_type: str (es. "casing")
            - material: str (es. "CF8M")
            - min_weight: float
            - max_weight: float

    Returns:
        Lista di pompe che soddisfano tutti i criteri
    """
    db = _load_raw()
    results = db

    family = query.get("pump_family")
    if family:
        results = [p for p in results
                   if p.get("pump_family", "").upper() == family.upper()]

    comp = query.get("component_type")
    if comp:
        results = [p for p in results
                   if p.get("component_type", "") == comp]

    mat = query.get("material")
    if mat:
        mat_lower = mat.lower()
        results = [p for p in results
                   if mat_lower in " ".join(p.get("materials", [])).lower()]

    min_w = query.get("min_weight")
    if min_w is not None:
        results = [p for p in results
                   if (p.get("weight_kg") or 0) >= min_w]

    max_w = query.get("max_weight")
    if max_w is not None:
        results = [p for p in results
                   if (p.get("weight_kg") or 0) <= max_w]

    return results


def delete_pump(source: str) -> bool:
    """Elimina una pompa dal database."""
    db = _load_raw()
    original_len = len(db)
    db = [p for p in db if p.get("source") != source]
    if len(db) < original_len:
        _save_raw(db)
        return True
    return False


def clear_database() -> int:
    """Svuota il database. Restituisce il numero di entry eliminate."""
    db = _load_raw()
    count = len(db)
    _save_raw([])
    return count


# ============================================================
# STATISTICHE
# ============================================================

def get_pump_stats() -> dict:
    """Statistiche aggregate sul database pompe."""
    db = _load_raw()
    if not db:
        return {"total": 0, "with_weight": 0}

    with_weight = [p for p in db if p.get("weight_kg") and p["weight_kg"] > 0]
    weights = [p["weight_kg"] for p in with_weight]

    # Famiglie
    families = {}
    for p in db:
        fam = p.get("pump_family", "N/D") or "N/D"
        families[fam] = families.get(fam, 0) + 1

    # Componenti
    components = {}
    for p in db:
        comp = p.get("component_type", "unknown")
        components[comp] = components.get(comp, 0) + 1

    # Materiali
    materials = {}
    for p in db:
        for mat in p.get("materials", []):
            materials[mat] = materials.get(mat, 0) + 1

    return {
        "total": len(db),
        "with_weight": len(with_weight),
        "families": families,
        "components": components,
        "materials": materials,
        "avg_weight": round(sum(weights) / len(weights), 1) if weights else 0,
        "max_weight": round(max(weights), 1) if weights else 0,
        "min_weight": round(min(weights), 1) if weights else 0,
        "weight_range": f"{min(weights):.0f} - {max(weights):.0f} kg" if weights else "N/D",
    }


# ============================================================
# RICERCA PARAMETRICA DISEGNI
# ============================================================

def _proximity_score(value: float, target: float, tolerance_pct: float = 30.0) -> float:
    """Calcola score di prossimità 0.0-1.0 tra due valori.

    tolerance_pct: percentuale di tolleranza (es. 30% = valori entro ±30% hanno score > 0).
    """
    if value <= 0 or target <= 0:
        return 0.0
    ratio = value / target
    # Score gaussiano: score=1.0 quando ratio=1.0, → 0 quando ratio fuori tolleranza
    deviation = abs(ratio - 1.0)
    threshold = tolerance_pct / 100.0
    if deviation > threshold:
        return 0.0
    return 1.0 - (deviation / threshold)


def search_similar_drawings(
    component_type: str,
    params: dict,
    top_k: int = 5,
) -> list[dict]:
    """Ricerca parametrica disegni simili per tipo componente.

    Per girante (impeller): tipo pompa + D2 + b2
    Per corpo (casing): tipo pompa + DN + diam. interno + larghezza voluta + rating
    Per coperchio (cover): tipo pompa + diametro esterno (D2)

    Args:
        component_type: 'impeller', 'casing', 'cover'
        params: Dict con i parametri di ricerca:
            - pump_family: str
            - d2_mm: float (diametro girante)
            - b2_mm: float (larghezza uscita)
            - dn_suction_mm: int (DN aspirazione)
            - dn_discharge_mm: int (DN mandata)
            - internal_diameter_mm: float
            - volute_width_mm: float
            - flange_rating: int
        top_k: numero massimo risultati

    Returns:
        Lista di dict con campi: pump data + 'score' (0-100) + 'match_details'
    """
    db = _load_raw()
    if not db:
        return []

    pump_family = params.get("pump_family", "").upper()
    scored = []

    for entry in db:
        score = 0.0
        details = []
        max_possible = 0.0

        # Ha peso? Necessario per essere utile come riferimento
        if not entry.get("weight_kg"):
            continue

        # --- Match famiglia: peso 30 (esatto) o 10 (simile) ---
        entry_family = (entry.get("pump_family") or "").upper()
        max_possible += 30
        if entry_family == pump_family:
            score += 30
            details.append(f"Famiglia: {entry_family} ✓")
        elif pump_family and entry_family and entry_family[:2] == pump_family[:2]:
            score += 10
            details.append(f"Famiglia simile: {entry_family} ~")

        # --- Match per tipo componente ---
        entry_comp = (entry.get("drawing_component") or entry.get("component_type", "")).lower()

        if component_type == "impeller":
            # Scarta se non è un disegno di girante (ma includi 'unknown')
            if entry_comp not in ("impeller", "unknown", ""):
                continue

            # D2: peso 40
            d2_target = params.get("d2_mm", 0)
            d2_entry = entry.get("d2_mm", 0)
            max_possible += 40
            if d2_target > 0 and d2_entry and d2_entry > 0:
                prox = _proximity_score(d2_entry, d2_target, 30)
                score += 40 * prox
                if prox > 0:
                    details.append(f"D2: {d2_entry:.0f}mm vs {d2_target:.0f}mm ({prox*100:.0f}%)")

            # b2: peso 20
            b2_target = params.get("b2_mm", 0)
            b2_entry = entry.get("b2_mm", 0)
            max_possible += 20
            if b2_target > 0 and b2_entry and b2_entry > 0:
                prox = _proximity_score(b2_entry, b2_target, 40)
                score += 20 * prox
                if prox > 0:
                    details.append(f"b2: {b2_entry:.0f}mm vs {b2_target:.0f}mm ({prox*100:.0f}%)")

            # Peso simile: bonus 10
            max_possible += 10

        elif component_type == "casing":
            if entry_comp not in ("casing", "unknown", ""):
                continue

            # DN aspirazione: peso 20
            dn_s_target = params.get("dn_suction_mm", 0)
            dn_s_entry = entry.get("dn_suction_mm", 0)
            max_possible += 20
            if dn_s_target and dn_s_entry:
                prox = _proximity_score(dn_s_entry, dn_s_target, 30)
                score += 20 * prox
                if prox > 0:
                    details.append(f"DN asp: {dn_s_entry} vs {dn_s_target}")

            # DN mandata: peso 15
            dn_d_target = params.get("dn_discharge_mm", 0)
            dn_d_entry = entry.get("dn_discharge_mm", 0)
            max_possible += 15
            if dn_d_target and dn_d_entry:
                prox = _proximity_score(dn_d_entry, dn_d_target, 30)
                score += 15 * prox
                if prox > 0:
                    details.append(f"DN mand: {dn_d_entry} vs {dn_d_target}")

            # Diametro interno: peso 15
            di_target = params.get("internal_diameter_mm", 0)
            di_entry = entry.get("internal_diameter_mm", 0)
            max_possible += 15
            if di_target and di_entry:
                prox = _proximity_score(di_entry, di_target, 25)
                score += 15 * prox

            # Rating: peso 10
            rat_target = params.get("flange_rating", 0)
            rat_entry = entry.get("flange_rating", 0)
            max_possible += 10
            if rat_target and rat_entry and rat_target == rat_entry:
                score += 10
                details.append(f"Rating: {rat_entry}# ✓")

            max_possible += 10  # bonus peso simile

        elif component_type == "cover":
            if entry_comp not in ("cover", "unknown", ""):
                continue

            # D2 (usato come proxy per diametro esterno coperchio): peso 50
            d2_target = params.get("d2_mm", 0)
            d2_entry = entry.get("d2_mm", 0)
            max_possible += 50
            if d2_target > 0 and d2_entry and d2_entry > 0:
                prox = _proximity_score(d2_entry, d2_target, 30)
                score += 50 * prox
                if prox > 0:
                    details.append(f"D ext: {d2_entry:.0f}mm vs {d2_target:.0f}mm")

            max_possible += 20  # bonus

        # Normalizza score a 0-100
        if max_possible > 0:
            normalized = (score / max_possible) * 100
        else:
            normalized = 0

        if normalized > 5:  # Soglia minima 5%
            result_entry = dict(entry)
            result_entry["score"] = round(normalized, 1)
            result_entry["match_details"] = details
            scored.append(result_entry)

    # Ordina per score decrescente
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ============================================================
# RICOSTRUZIONE DA QDRANT
# ============================================================

def rebuild_from_qdrant() -> int:
    """Ricostruisce il database pompe analizzando tutti i documenti in Qdrant.

    Returns:
        Numero di pompe estratte
    """
    try:
        from modules.drawing_analysis import get_all_documents_from_qdrant
        from weight_engine.pump_data_extractor import extract_pump_data
    except ImportError as e:
        logger.error(f"Import error per rebuild: {e}")
        return 0

    documents = get_all_documents_from_qdrant()
    if not documents:
        logger.warning("Nessun documento trovato in Qdrant per rebuild")
        return 0

    count = 0
    for doc in documents:
        source = doc.get("source", "")
        text = doc.get("total_text", "")

        if not text or len(text) < 50:
            continue

        # Estrai dati strutturati
        pump_data = extract_pump_data(text, source)

        # Salva solo se ha almeno un dato utile
        has_useful_data = (
            pump_data.get("weight_kg") is not None
            or pump_data.get("materials")
            or pump_data.get("component_type") != "unknown"
        )

        if has_useful_data:
            save_pump_data(pump_data)
            count += 1
            logger.debug(f"Estratto: {os.path.basename(source)} -> "
                        f"weight={pump_data.get('weight_kg')}, "
                        f"comp={pump_data.get('component_type')}")

    logger.info(f"Rebuild completato: {count}/{len(documents)} documenti con dati utili")
    return count


# ============================================================
# IO
# ============================================================

def _load_raw() -> list:
    """Carica il database JSON."""
    if not os.path.exists(_DB_FILE):
        return []
    try:
        with open(_DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_raw(data: list):
    """Salva il database JSON."""
    with open(_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
