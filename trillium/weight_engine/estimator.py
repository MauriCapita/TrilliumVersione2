"""
Trillium V2 — Weight Estimation Engine
Motore principale per la stima dei pesi dei componenti di pompe centrifughe.
Implementa le formule di scaling e calcolo geometrico.
"""

import math
import uuid
import logging
from datetime import datetime
from typing import Optional

from .materials import (
    get_density, density_ratio, get_flange_weight,
    get_properties, MATERIAL_DENSITY,
)
from .parts_list import (
    get_parts_template, get_family_info, CALC_METHODS,
)

logger = logging.getLogger(__name__)


# ============================================================
# DATACLASS-LIKE: RISULTATO STIMA SINGOLO COMPONENTE
# ============================================================

class ComponentEstimate:
    """Risultato della stima di peso per un singolo componente."""

    def __init__(self, component_name: str, group: str, calc_method: str):
        self.component_name = component_name
        self.group = group
        self.calc_method = calc_method
        self.ref_weight_kg: Optional[float] = None
        self.ref_material: Optional[str] = None
        self.ref_source: Optional[str] = None
        self.estimated_weight_kg: Optional[float] = None
        self.factors_applied: dict = {}
        self.notes: str = ""
        self.confidence: str = "N/A"  # alta, media, bassa, N/A
        self.warnings: list[str] = []
        self.is_estimated: bool = False
        self.calculation_details: dict = {}  # formula, inputs, steps

    def to_dict(self) -> dict:
        return {
            "Componente": self.component_name,
            "Gruppo": self.group,
            "Metodo": self.calc_method,
            "Peso Rif. (kg)": self.ref_weight_kg,
            "Materiale Rif.": self.ref_material,
            "Sorgente Rif.": self.ref_source,
            "Peso Stimato (kg)": self.estimated_weight_kg,
            "Fattori Applicati": str(self.factors_applied) if self.factors_applied else "",
            "Confidenza": self.confidence,
            "Note": self.notes,
            "Warning": "; ".join(self.warnings) if self.warnings else "",
        }


# ============================================================
# DATACLASS-LIKE: RISULTATO STIMA COMPLETA
# ============================================================

class EstimationResult:
    """Risultato completo della stima pesi per una pompa."""

    def __init__(self, params: dict):
        self.job_id = str(uuid.uuid4())[:8].upper()
        self.timestamp = datetime.now()
        self.params = params
        self.components: list[ComponentEstimate] = []
        self.total_weight_kg: float = 0.0
        self.warnings: list[str] = []
        self.log_entries: list[str] = []
        self.ref_pump_info: Optional[dict] = None

    def add_log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_entries.append(f"[{ts}] {message}")
        logger.info(message)

    def calculate_total(self):
        self.total_weight_kg = sum(
            c.estimated_weight_kg for c in self.components
            if c.estimated_weight_kg is not None
        )

    def summary_dict(self) -> dict:
        return {
            "Job ID": self.job_id,
            "Data/Ora": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Famiglia Pompa": self.params.get("pump_family", ""),
            "Nq": self.params.get("nq", ""),
            "Scale Factor (f)": self.params.get("scale_factor", ""),
            "Pressione (bar)": self.params.get("pressure", ""),
            "Temperatura (°C)": self.params.get("temperature", ""),
            "Materiale": self.params.get("material", ""),
            "Flange Rating": self.params.get("flange_rating", ""),
            "Spessore Parete (mm)": self.params.get("wall_thickness", ""),
            "Peso Totale Stimato (kg)": round(self.total_weight_kg, 1),
            "Componenti Stimati": len([c for c in self.components if c.is_estimated]),
            "Componenti Totali": len(self.components),
            "Warning": len(self.warnings),
        }


# ============================================================
# FORMULE DI SCALING
# ============================================================

def scale_weight_complex(
    weight_ref: float,
    scale_factor: float,
    rho_new: float,
    rho_ref: float,
    exponent: float = 2.35,
) -> float:
    """
    Formula scaling per componenti di fusione (casting).
    pnew = pref × f^exp × ρnew/ρref

    Args:
        weight_ref: Peso del componente di riferimento (kg)
        scale_factor: Fattore di scala f (rapporto diametri giranti)
        rho_new: Densità materiale nuovo (kg/m³)
        rho_ref: Densità materiale riferimento (kg/m³)
        exponent: Esponente scaling (2.3÷2.4, default 2.35)

    Returns:
        Peso stimato (kg)
    """
    if weight_ref <= 0 or scale_factor <= 0 or rho_new <= 0 or rho_ref <= 0:
        return 0.0

    return weight_ref * (scale_factor ** exponent) * (rho_new / rho_ref)


def scale_weight_pressure(
    weight_ref: float,
    scale_factor: float,
    rho_new: float,
    rho_ref: float,
    thickness_new: float,
    thickness_ref: float,
) -> float:
    """
    Formula scaling per componenti pressurizzati (con rapporto spessori).
    pnew = pref × f^2 × ρnew/ρref × Snew/Sref

    Args:
        weight_ref: Peso del componente di riferimento (kg)
        scale_factor: Fattore di scala f
        rho_new: Densità materiale nuovo (kg/m³)
        rho_ref: Densità materiale riferimento (kg/m³)
        thickness_new: Spessore nominale nuovo (mm)
        thickness_ref: Spessore nominale riferimento (mm)

    Returns:
        Peso stimato (kg)
    """
    if (weight_ref <= 0 or scale_factor <= 0 or rho_new <= 0
            or rho_ref <= 0 or thickness_new <= 0 or thickness_ref <= 0):
        return 0.0

    return (weight_ref * (scale_factor ** 2)
            * (rho_new / rho_ref)
            * (thickness_new / thickness_ref))


def calc_cylinder_weight(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    length_mm: float,
    density_kg_m3: float,
) -> float:
    """
    Peso di un cilindro cavo (es. colonna, albero, tubo).
    W = π/4 × (D² - d²) × L × ρ

    Args:
        outer_diameter_mm: Diametro esterno (mm)
        inner_diameter_mm: Diametro interno (mm), 0 per pieno
        length_mm: Lunghezza (mm)
        density_kg_m3: Densità (kg/m³)

    Returns:
        Peso (kg)
    """
    D = outer_diameter_mm / 1000  # m
    d = inner_diameter_mm / 1000  # m
    L = length_mm / 1000  # m

    volume = (math.pi / 4) * (D**2 - d**2) * L
    return volume * density_kg_m3


def calc_cone_weight(
    D_large_mm: float,
    D_small_mm: float,
    length_mm: float,
    thickness_mm: float,
    density_kg_m3: float,
) -> float:
    """
    Peso approssimato di un cono (es. supporto motore, transizione).
    Calcolo semplificato come tronco di cono.
    """
    D1 = D_large_mm / 1000
    D2 = D_small_mm / 1000
    L = length_mm / 1000
    t = thickness_mm / 1000

    R1 = D1 / 2
    R2 = D2 / 2
    slant = math.sqrt(L**2 + (R1 - R2)**2)

    # Area laterale media × spessore → volume
    circumference_avg = math.pi * (R1 + R2)
    volume = circumference_avg * slant * t
    return volume * density_kg_m3


def calc_ring_weight(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    height_mm: float,
    density_kg_m3: float,
) -> float:
    """
    Peso di un anello (es. wear ring, flange).
    """
    return calc_cylinder_weight(
        outer_diameter_mm, inner_diameter_mm, height_mm, density_kg_m3
    )


# ============================================================
# MOTORE DI STIMA PRINCIPALE
# ============================================================

class WeightEstimator:
    """
    Motore principale per la stima dei pesi dei componenti di pompe.

    Flusso:
    1. Riceve parametri input (famiglia, Nq, f, pressione, temperatura, materiale, ecc.)
    2. Carica template componenti per la famiglia
    3. Per ogni componente, applica il metodo di calcolo appropriato
    4. Se disponibile una pompa di riferimento (da RAG), usa i pesi misurati come base
    5. Genera il risultato completo con tracciabilità
    """

    def __init__(self):
        self.reference_pump: Optional[dict] = None

    def set_reference_pump(self, ref_data: dict):
        """
        Imposta la pompa di riferimento trovata via RAG.

        ref_data dovrebbe contenere:
        {
            "source": "nome documento/disegno sorgente",
            "pump_family": "OH2",
            "nq": 25,
            "impeller_diameter": 250,
            "material": "A216 WCB",
            "wall_thickness": 12.0,
            "components": {
                "Casing": {"weight_kg": 150, "material": "A216 WCB"},
                "Impeller": {"weight_kg": 25, "material": "A216 WCB"},
                ...
            }
        }
        """
        self.reference_pump = ref_data

    def estimate(self, params: dict) -> EstimationResult:
        """
        Esegue la stima completa dei pesi.

        Args:
            params: Dizionario con parametri input:
                - pump_family: str (es. "OH2", "BB5", "VS6")
                - nq: float (velocità specifica)
                - scale_factor: float (fattore di scala f)
                - pressure: float (pressione bar)
                - temperature: float (temperatura °C)
                - material: str (materiale principale)
                - flange_rating: int (rating flange: 150, 300, 600, ...)
                - wall_thickness: float (spessore parete mm)
                - num_stages: int (numero stadi, default 1)
                - suction_size_inch: float (apertura aspirazione in pollici)
                - discharge_size_inch: float (apertura mandata in pollici)

        Returns:
            EstimationResult con tutti i componenti stimati
        """
        result = EstimationResult(params)
        result.add_log(f"Avvio stima – Job ID: {result.job_id}")
        result.add_log(f"Famiglia pompa: {params.get('pump_family', 'N/D')}")

        # 1. Validazione input
        validation_ok = self._validate_params(params, result)
        if not validation_ok:
            result.add_log("ERRORE: Validazione fallita, stima interrotta")
            return result

        # 2. Carica template componenti
        pump_family = params["pump_family"].upper()
        template = get_parts_template(pump_family)
        family_info = get_family_info(pump_family)

        if not template:
            result.warnings.append(f"Famiglia pompa '{pump_family}' non trovata")
            result.add_log(f"ERRORE: template non trovato per {pump_family}")
            return result

        result.add_log(f"Template caricato: {family_info['name']} ({len(template)} componenti)")

        # 3. Risolvi densità materiale
        material = params["material"]
        rho_new = get_density(material)
        if rho_new is None:
            result.warnings.append(f"Materiale '{material}' non trovato nel database. Usando acciaio al carbonio (7850 kg/m³)")
            rho_new = 7850
            result.add_log(f"WARNING: materiale '{material}' non trovato, fallback a Carbon Steel")
        else:
            result.add_log(f"Materiale: {material} (ρ = {rho_new} kg/m³)")

        # 4. Verifica compatibilità materiale-temperatura
        mat_props = get_properties(material)
        if mat_props:
            temp = params.get("temperature", 0)
            if temp > mat_props.get("temperature_limit", 9999):
                warning = (f"ATTENZIONE: temperatura {temp}°C supera il limite "
                           f"del materiale {material} ({mat_props['temperature_limit']}°C)")
                result.warnings.append(warning)
                result.add_log(f"WARNING: {warning}")

        # 5. Imposta riferimenti
        ref_material = "Carbon Steel"
        rho_ref = MATERIAL_DENSITY.get(ref_material, 7850)
        scale_factor = params.get("scale_factor", 1.0)
        d2_mm = params.get("d2_mm", 0)
        wall_thickness_new = params.get("wall_thickness", 0)
        num_stages = params.get("num_stages", 1)

        # 5b. Ricerca parametrica disegni simili (se D2 disponibile)
        similar_drawings = {"impeller": [], "casing": [], "cover": []}
        if d2_mm > 0:
            try:
                from .pump_database import search_similar_drawings
                from .nq_curve import calc_b2
                nq = params.get("nq", 30)
                b2_mm = calc_b2(nq, d2_mm) if nq > 0 else 0

                search_params = {
                    "pump_family": pump_family,
                    "d2_mm": d2_mm,
                    "b2_mm": b2_mm,
                    "dn_suction_mm": params.get("suction_size_inch", 0) * 25.4 if params.get("suction_size_inch", 0) else 0,
                    "dn_discharge_mm": params.get("discharge_size_inch", 0) * 25.4 if params.get("discharge_size_inch", 0) else 0,
                    "flange_rating": params.get("flange_rating", 0),
                }

                for comp_type in ["impeller", "casing", "cover"]:
                    results = search_similar_drawings(comp_type, search_params, top_k=3)
                    similar_drawings[comp_type] = results
                    if results:
                        result.add_log(
                            f"  Disegni simili ({comp_type}): {len(results)} trovati, "
                            f"migliore: {results[0].get('filename', '?')} ({results[0]['score']:.0f}%)"
                        )
            except Exception as e:
                result.add_log(f"  Ricerca parametrica fallita: {e}")

        # 5c. Se ho un disegno simile come riferimento, calcola scale_factor da D2
        if d2_mm > 0 and similar_drawings.get("impeller"):
            best_impeller = similar_drawings["impeller"][0]
            d2_ref = best_impeller.get("d2_mm", 0)
            if d2_ref and d2_ref > 0:
                scale_factor = d2_mm / d2_ref
                result.add_log(f"Scale factor auto-calcolato: D2_new/D2_ref = {d2_mm}/{d2_ref} = {scale_factor:.3f}")

        if self.reference_pump:
            ref_material = self.reference_pump.get("material", ref_material)
            rho_ref_lookup = get_density(ref_material)
            if rho_ref_lookup:
                rho_ref = rho_ref_lookup
            result.ref_pump_info = self.reference_pump
            result.add_log(f"Pompa riferimento: {self.reference_pump.get('source', 'N/D')}")
            result.add_log(f"Materiale riferimento: {ref_material} (ρ = {rho_ref} kg/m³)")
        else:
            result.add_log("Nessuna pompa di riferimento specifica. Usando stime parametriche.")

        result.add_log(f"Scale factor: f = {scale_factor:.3f}")
        result.add_log(f"Rapporto densità: ρnew/ρref = {rho_new/rho_ref:.4f}")

        # 6. Stima ogni componente
        for comp_def in template:
            comp = ComponentEstimate(
                component_name=comp_def["component"],
                group=comp_def["group"],
                calc_method=comp_def["calc_method"],
            )

            # Cerca peso di riferimento nella pompa di riferimento
            ref_weight = self._get_ref_weight(comp_def["component"])
            ref_mat = ref_material
            ref_source = self.reference_pump.get("source", "N/D") if self.reference_pump else "Stima parametrica"

            # Fallback: cerca peso dal disegno simile trovato per ricerca parametrica
            if not ref_weight and similar_drawings:
                comp_name_lower = comp_def["component"].lower()
                drawing_type = None

                # Solo componenti principali usano disegni come riferimento
                # Escludi viteria, cuscinetti, boccole, baderna, protezione, conservazione, varie
                skip_keywords = ["viteria", "cuscinetto", "boccola", "premitreccia",
                                 "baderna", "protezione", "conservazione", "varie",
                                 "bulloni", "anello baderna", "anello usura"]
                if not any(kw in comp_name_lower for kw in skip_keywords):
                    if "girante" in comp_name_lower or "impeller" in comp_name_lower:
                        drawing_type = "impeller"
                    elif ("corpo" in comp_name_lower or "voluta" in comp_name_lower) and "supporto" not in comp_name_lower and "supp" not in comp_name_lower:
                        drawing_type = "casing"
                    elif "coperchio corpo" in comp_name_lower or ("cover" in comp_name_lower and "supp" not in comp_name_lower):
                        drawing_type = "cover"

                if drawing_type and similar_drawings.get(drawing_type):
                    best = similar_drawings[drawing_type][0]
                    if best.get("weight_kg") and best["weight_kg"] > 0:
                        ref_weight = best["weight_kg"]
                        ref_source = f"Disegno simile: {best.get('filename', '?')} ({best['score']:.0f}%)"
                        if best.get("material_primary"):
                            ref_mat = best["material_primary"]
                            rho_ref_draw = get_density(ref_mat)
                            if rho_ref_draw:
                                rho_ref = rho_ref_draw

            # Moltiplica per stadi se necessario
            multiplier = 1
            if "per stadio" in comp_def["component"].lower() and num_stages > 1:
                multiplier = num_stages
                comp.notes = f"× {num_stages} stadi"

            if comp_def["calc_method"] == "scaling_complex":
                if ref_weight:
                    est = scale_weight_complex(ref_weight, scale_factor, rho_new, rho_ref)
                    comp.ref_weight_kg = ref_weight
                    comp.estimated_weight_kg = round(est * multiplier, 2)
                    comp.factors_applied = {
                        "f": scale_factor, "exp": 2.35,
                        "ρ_ratio": round(rho_new/rho_ref, 4),
                    }
                    comp.confidence = "alta" if ref_weight > 0 else "media"
                    comp.is_estimated = True
                    comp.calculation_details = {
                        "formula": "pnew = pref × f^exp × ρnew/ρref",
                        "inputs": {
                            "pref (peso riferimento)": f"{ref_weight} kg",
                            "f (scale factor)": f"{scale_factor}",
                            "esponente": "2.35",
                            "ρnew": f"{rho_new} kg/m³ ({material})",
                            "ρref": f"{rho_ref} kg/m³ ({ref_material})",
                        },
                        "steps": [
                            f"f^2.35 = {scale_factor}^2.35 = {scale_factor**2.35:.4f}",
                            f"ρnew/ρref = {rho_new}/{rho_ref} = {rho_new/rho_ref:.4f}",
                            f"pnew = {ref_weight} × {scale_factor**2.35:.4f} × {rho_new/rho_ref:.4f} = {est:.2f} kg",
                        ],
                    }
                    if multiplier > 1:
                        comp.calculation_details["steps"].append(
                            f"× {multiplier} stadi = {est * multiplier:.2f} kg"
                        )
                else:
                    # Stima parametrica senza riferimento
                    est_base = self._parametric_estimate(comp_def, params, rho_new)
                    if est_base > 0:
                        comp.estimated_weight_kg = round(est_base * multiplier, 2)
                        comp.confidence = "bassa"
                        comp.is_estimated = True
                        comp.notes += " (stima parametrica, no riferimento)"
                        comp.calculation_details = {
                            "formula": "Correlazione empirica (Nq, f, ρ)",
                            "inputs": {"Nq": str(params.get('nq',30)), "f": str(scale_factor), "ρ": f"{rho_new} kg/m³"},
                            "steps": [f"Base empirica = {est_base:.2f} kg (parametrica)"],
                        }
                    else:
                        comp.warnings.append("Dati insufficienti per stima")

            elif comp_def["calc_method"] == "scaling_pressure":
                wall_thickness_ref = self.reference_pump.get("wall_thickness", wall_thickness_new) if self.reference_pump else wall_thickness_new
                if ref_weight and wall_thickness_new > 0 and wall_thickness_ref > 0:
                    est = scale_weight_pressure(
                        ref_weight, scale_factor,
                        rho_new, rho_ref,
                        wall_thickness_new, wall_thickness_ref,
                    )
                    comp.ref_weight_kg = ref_weight
                    comp.estimated_weight_kg = round(est * multiplier, 2)
                    comp.factors_applied = {
                        "f": scale_factor,
                        "ρ_ratio": round(rho_new/rho_ref, 4),
                        "S_ratio": round(wall_thickness_new/wall_thickness_ref, 4),
                    }
                    comp.confidence = "alta"
                    comp.is_estimated = True
                    comp.calculation_details = {
                        "formula": "pnew = pref × f² × ρnew/ρref × Snew/Sref",
                        "inputs": {
                            "pref": f"{ref_weight} kg",
                            "f": str(scale_factor),
                            "ρnew": f"{rho_new} kg/m³", "ρref": f"{rho_ref} kg/m³",
                            "Snew": f"{wall_thickness_new} mm", "Sref": f"{wall_thickness_ref} mm",
                        },
                        "steps": [
                            f"f² = {scale_factor}² = {scale_factor**2:.4f}",
                            f"ρnew/ρref = {rho_new/rho_ref:.4f}",
                            f"Snew/Sref = {wall_thickness_new}/{wall_thickness_ref} = {wall_thickness_new/wall_thickness_ref:.4f}",
                            f"pnew = {ref_weight} × {scale_factor**2:.4f} × {rho_new/rho_ref:.4f} × {wall_thickness_new/wall_thickness_ref:.4f} = {est:.2f} kg",
                        ],
                    }
                elif ref_weight:
                    # Senza spessore, usa formula complex come fallback
                    est = scale_weight_complex(ref_weight, scale_factor, rho_new, rho_ref, exponent=2.0)
                    comp.ref_weight_kg = ref_weight
                    comp.estimated_weight_kg = round(est * multiplier, 2)
                    comp.factors_applied = {"f": scale_factor, "exp": 2.0, "ρ_ratio": round(rho_new/rho_ref, 4)}
                    comp.confidence = "media"
                    comp.is_estimated = True
                    comp.warnings.append("Spessore non disponibile, usata formula semplificata f²")
                    comp.calculation_details = {
                        "formula": "pnew = pref × f² × ρnew/ρref (senza spessore)",
                        "inputs": {"pref": f"{ref_weight} kg", "f": str(scale_factor)},
                        "steps": [f"Fallback: {ref_weight} × {scale_factor**2:.4f} × {rho_new/rho_ref:.4f} = {est:.2f} kg"],
                    }
                else:
                    est_base = self._parametric_estimate(comp_def, params, rho_new)
                    if est_base > 0:
                        comp.estimated_weight_kg = round(est_base * multiplier, 2)
                        comp.confidence = "bassa"
                        comp.is_estimated = True
                        comp.notes += " (stima parametrica)"
                        comp.calculation_details = {
                            "formula": "Correlazione empirica",
                            "inputs": {},
                            "steps": [f"Parametrica: {est_base:.2f} kg"],
                        }

            elif comp_def["calc_method"] == "geometric":
                est_base = self._geometric_estimate(comp_def, params, rho_new)
                if est_base > 0:
                    comp.estimated_weight_kg = round(est_base * multiplier, 2)
                    comp.confidence = "media"
                    comp.is_estimated = True
                elif ref_weight:
                    est = scale_weight_complex(ref_weight, scale_factor, rho_new, rho_ref, exponent=2.0)
                    comp.ref_weight_kg = ref_weight
                    comp.estimated_weight_kg = round(est * multiplier, 2)
                    comp.confidence = "media"
                    comp.is_estimated = True
                    comp.notes += " (scaling da riferimento, no geometria)"

            elif comp_def["calc_method"] == "lookup_flange":
                self._estimate_flange(comp, comp_def, params, material)

            elif comp_def["calc_method"] == "lookup_standard":
                if ref_weight:
                    comp.ref_weight_kg = ref_weight
                    comp.estimated_weight_kg = round(ref_weight * (rho_new / rho_ref) * multiplier, 2)
                    comp.confidence = "alta"
                    comp.is_estimated = True
                    comp.factors_applied = {"ρ_ratio": round(rho_new/rho_ref, 4)}
                    comp.calculation_details = {
                        "formula": "pnew = pref × ρnew/ρref (peso da catalogo)",
                        "inputs": {"pref": f"{ref_weight} kg", "ρ_ratio": f"{rho_new/rho_ref:.4f}"},
                        "steps": [f"{ref_weight} × {rho_new/rho_ref:.4f} = {ref_weight * rho_new/rho_ref:.2f} kg"],
                    }
                else:
                    comp.confidence = "N/A"
                    comp.warnings.append("Peso da catalogo non disponibile, serve dato specifico")

            elif comp_def["calc_method"] == "ai_estimate":
                comp.confidence = "bassa"
                comp.warnings.append("Stima AI non ancora implementata, richiede query RAG")

            comp.ref_material = ref_mat
            comp.ref_source = ref_source
            result.components.append(comp)

            if comp.is_estimated:
                result.add_log(
                    f"  ✓ {comp.component_name}: {comp.estimated_weight_kg} kg "
                    f"({comp.confidence}) [{comp.calc_method}]"
                )
            else:
                result.add_log(
                    f"  ✗ {comp.component_name}: non stimato "
                    f"({'; '.join(comp.warnings) if comp.warnings else 'dati insufficienti'})"
                )

        # 7. Calcola totale
        result.calculate_total()
        result.add_log(f"Peso totale stimato: {result.total_weight_kg:.1f} kg")
        result.add_log(f"Componenti stimati: {len([c for c in result.components if c.is_estimated])}/{len(result.components)}")
        result.add_log(f"Stima completata — Job ID: {result.job_id}")

        return result

    def _validate_params(self, params: dict, result: EstimationResult) -> bool:
        """Validazione parametri input."""
        ok = True

        required = ["pump_family", "material"]
        for field in required:
            if not params.get(field):
                result.warnings.append(f"Campo obbligatorio mancante: {field}")
                ok = False

        if params.get("scale_factor", 0) <= 0:
            params["scale_factor"] = 1.0
            result.add_log("Scale factor non specificato, impostato a 1.0")

        if params.get("nq", 0) <= 0:
            result.warnings.append("Nq (velocità specifica) non specificata")
            result.add_log("WARNING: Nq non specificato")

        return ok

    def _get_ref_weight(self, component_name: str) -> Optional[float]:
        """Cerca il peso di un componente nella pompa di riferimento."""
        if not self.reference_pump or "components" not in self.reference_pump:
            return None

        components = self.reference_pump["components"]

        # Match esatto
        if component_name in components:
            return components[component_name].get("weight_kg")

        # Match parziale
        name_lower = component_name.lower()
        for key, data in components.items():
            if key.lower() in name_lower or name_lower in key.lower():
                return data.get("weight_kg")

        # Match per keyword
        keywords = {
            "casing": ["casing", "corpo", "barrel"],
            "impeller": ["impeller", "girante"],
            "shaft": ["shaft", "albero"],
            "bearing": ["bearing", "cuscinetto"],
            "seal": ["seal", "tenuta"],
            "flange": ["flange", "flangia"],
            "wear": ["wear ring", "anello"],
            "diffuser": ["diffuser", "diffusore"],
            "bowl": ["bowl"],
            "column": ["column", "colonna"],
            "balance": ["balance drum", "balance disc"],
        }

        for category, kws in keywords.items():
            if any(kw in name_lower for kw in kws):
                for key, data in components.items():
                    if any(kw in key.lower() for kw in kws):
                        return data.get("weight_kg")

        return None

    def _parametric_estimate(self, comp_def: dict, params: dict, rho: float) -> float:
        """
        Stima parametrica quando non c'è pompa di riferimento.
        Usa correlazioni empiriche basilari basate su Nq e Scale Factor.
        """
        nq = params.get("nq", 30)
        f = params.get("scale_factor", 1.0)
        name = comp_def["component"].lower()

        # Correlazioni empiriche molto approssimate
        # (saranno migliorate dal matching AI con pompe reali)
        base = 0

        if "impeller" in name or "girante" in name:
            base = 0.5 * nq * f**2.35  # kg, molto approssimato
        elif "casing" in name or "corpo" in name or "barrel" in name or "voluta" in name:
            base = 2.0 * nq * f**2.35
        elif "bowl" in name:
            base = 1.0 * nq * f**2.35
        elif "diffuser" in name:
            base = 0.8 * nq * f**2.35
        elif "shaft" in name or "albero" in name:
            base = 0.3 * nq * f**2.0
        elif "wear" in name or "anello usura" in name:
            base = 0.05 * nq * f**2.0
        elif "seal" in name or "tenuta" in name or "boccola" in name:
            base = 5.0  # peso medio tenuta meccanica
        elif "premitreccia" in name or "baderna" in name:
            base = 3.0  # peso medio premitreccia/baderna
        elif "cuscinetto" in name and "supporto" not in name:
            base = 3.0  # peso medio cuscinetto
        elif "bearing housing" in name or "supporto" in name:
            base = 0.2 * nq * f**2.0
        elif "camicia" in name or "sleeve" in name:
            base = 0.1 * nq * f**2.0
        elif "balance" in name:
            base = 0.3 * nq * f**2.35
        elif "cover" in name or "coperchio" in name:
            base = 0.8 * nq * f**2.0
        elif "baseplate" in name or "sole" in name or "piastra" in name:
            base = 1.5 * nq * f**2.0
        elif "bulloni" in name or "viteria" in name:
            base = 0.05 * nq * f**2.0  # bulloneria leggera
        elif "protezione" in name or "guard" in name:
            base = 5.0  # peso fisso carter giunto

        if base > 0:
            # Scala per densità rispetto all'acciaio al carbonio
            base *= rho / 7850
            return base

        return 0

    def _geometric_estimate(self, comp_def: dict, params: dict, rho: float) -> float:
        """Stima geometrica per componenti semplici."""
        name = comp_def["component"].lower()
        f = params.get("scale_factor", 1.0)
        nq = params.get("nq", 30)

        # Shaft / Albero: stima diametro e lunghezza da Nq e f
        if ("shaft" in name or "albero" in name) and "camicia" not in name and "sleeve" not in name:
            diameter_mm = 40 + nq * 1.5 * f  # mm
            if "line shaft" in name:
                length_mm = 3000 * f  # Albero lungo per VS
            else:
                length_mm = 500 * f  # Albero corto per OH
            return calc_cylinder_weight(diameter_mm, 0, length_mm, rho)

        # Camicia protezione albero / Shaft sleeve
        if "camicia" in name or ("sleeve" in name and "shaft" in name):
            shaft_d = 40 + nq * 1.5 * f
            outer_d = shaft_d + 6  # 3mm spessore
            inner_d = shaft_d
            length = 150 * f
            return calc_cylinder_weight(outer_d, inner_d, length, rho)

        # Anello usura (wear ring) - cilindro cavo
        if "anello usura" in name or "wear ring" in name:
            d2 = params.get("d2_mm", 200 * f)
            outer_d = d2 * 0.6  # tipicamente 60% del D2
            inner_d = outer_d - 6  # spessore 3mm
            height = 20 * f  # altezza ~20mm scalata
            qty = comp_def.get("qty", 1)
            return calc_ring_weight(outer_d, inner_d, height, rho) * qty

        # Piastra di base / Baseplate
        if "piastra" in name or "baseplate" in name or "sole plate" in name:
            # Piastra rettangolare approssimata: L × W × spessore
            length_mm = 800 * f  # mm
            width_mm = 500 * f   # mm
            thickness_mm = 25    # costante
            volume = (length_mm * width_mm * thickness_mm) / 1e9  # m³
            return volume * rho

        # Bulloni fondazione / Foundation bolts
        if "bulloni" in name and "fondazione" in name:
            # 4 bulloni M24 × 500mm ciascuno
            bolt_d = 24  # mm
            bolt_l = 500  # mm
            n_bolts = 4
            single = calc_cylinder_weight(bolt_d, 0, bolt_l, rho)
            return single * n_bolts

        # Viteria corpo / Cover bolts
        if "viteria" in name:
            # Stima ~2% del peso stimabile dei componenti principali
            # Approssimato come peso empirico basato su scala
            return 0.5 * nq * f**1.5 * (rho / 7850)

        # Column pipe
        if "column" in name and "pipe" in name:
            outer_d = 200 * f  # mm
            inner_d = outer_d - 20  # spessore 10mm
            length = 3000  # 3m per sezione
            return calc_cylinder_weight(outer_d, inner_d, length, rho)

        return 0

    def _estimate_flange(self, comp: ComponentEstimate, comp_def: dict,
                         params: dict, material: str):
        """Stima peso flange da tabella ASME B16.5."""
        rating = params.get("flange_rating", 150)
        name = comp_def["component"].lower()

        if "suction" in name:
            size = params.get("suction_size_inch", 8)
        elif "discharge" in name:
            size = params.get("discharge_size_inch", 6)
        else:
            size = params.get("discharge_size_inch", 6)

        weight = get_flange_weight(size, rating, material)
        if weight:
            comp.estimated_weight_kg = weight
            comp.confidence = "alta"
            comp.is_estimated = True
            comp.factors_applied = {"size_inch": size, "rating": rating}
            comp.notes = f"ASME B16.5, {size}\" × {rating}#"
            comp.calculation_details = {
                "formula": "Tabella ASME B16.5",
                "inputs": {"Dimensione": f"{size}\"", "Rating": f"{rating}#", "Materiale": material},
                "steps": [f"Lookup: ({size}\", {rating}#) → {weight} kg"],
            }
        else:
            comp.warnings.append(f"Combinazione flange ({size}\", {rating}#) non trovata in tabella")


# ============================================================
# FUNZIONE CONVENIENCE
# ============================================================

def run_estimation(params: dict, reference_pump: dict = None) -> EstimationResult:
    """
    Funzione convenience per eseguire una stima completa.

    Args:
        params: Parametri input pompa
        reference_pump: Dati pompa di riferimento (opzionale, da RAG)

    Returns:
        EstimationResult
    """
    estimator = WeightEstimator()
    if reference_pump:
        estimator.set_reference_pump(reference_pump)
    return estimator.estimate(params)
