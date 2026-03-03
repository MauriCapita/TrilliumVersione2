"""
Trillium RAG - Mapping SOP ↔ Mod (Moduli di Calcolo)
Derivato da Technical Documentation Project/00_INDEX.md
Permette di collegare automaticamente le procedure ai moduli Excel associati.
"""

import os
import re

# ============================================================
# MAPPING SOP → Mod
# Chiave: numero SOP (es. "SOP-521")
# Valore: lista di Mod collegati (es. ["Mod.497"])
# ============================================================

SOP_TO_MOD = {
    # --- Rotordynamics / Critical Speed / Torsional ---
    "SOP-452": ["Mod.423"],          # Level 2 Undamped - Critical speed calculator
    "SOP-457": ["Mod.423"],          # Level 2 First dry critical speed
    "SOP-460": ["Mod.407", "Mod.408", "Mod.409"],  # Torsional analysis
    "SOP-473": ["Mod.423"],          # Level 1 Lateral - First rotor critical speed
    "SOP-474": ["Mod.423"],          # Level 1 First rotor critical speed
    "SOP-557": ["Mod.539"],          # Level 3 Transient forced response

    # --- Hydraulics / NPSH / Performance ---
    "SOP-461": ["Mod.414"],          # Minimum Continuous Stable Flow (MCSF)
    "SOP-471": ["Mod.421"],          # NPSHr 40000h - Vlaming formula
    "SOP-475": ["Mod.465"],          # Refiguring from Tested Data
    "SOP-483": ["Mod.465"],          # Refiguring from surface finish
    "SOP-485": ["Mod.467"],          # Refiguring from Clearance Change
    "SOP-489": ["Mod.469"],          # High-Medium-Low Energy categorization
    "SOP-498": ["Mod.471"],          # Trimming Coefficients Definition
    "SOP-549": ["Mod.532"],          # Impeller hydraulic radial thrust
    "SOP-550": ["Mod.533"],          # NPSHR safety margin
    "SOP-566": ["Mod.530"],          # Impeller Minimum Trimming Diameter
    "SOP-567": ["Mod.414"],          # Pump Minimum Flow Determination

    # --- Balance Disc / Drum ---
    "SOP-472": ["Mod.422"],          # Balance disc
    "SOP-548": ["Mod.531"],          # Balance drum design

    # --- Mechanical: Bolt / Gasket / Joint ---
    "SOP-477": ["Mod.432"],          # Bolted joint verification
    "SOP-521": ["Mod.497"],          # Bolts tightening torque
    "SOP-527": ["Mod.498", "Mod.499", "Mod.501"],  # Gasket selection
    "SOP-528": ["Mod.500"],          # Oil ring calculation
    "SOP-573": ["Mod.551"],          # Barrel and cover bolted design
    "SOP-583": ["Mod.498", "Mod.499"],  # Gasket design axially split

    # --- Bearing ---
    "SOP-576": ["Mod.428"],          # Thrust bearing selection
    "SOP-580": ["Mod.427"],          # Bearing type selection

    # --- Shaft / Keys ---
    "SOP-558": ["Mod.502", "Mod.503"],  # Minimum shaft diameter (bolt/stud create)
    "SOP-561": ["Mod.1140"],         # Keys verification

    # --- Other ---
    "SOP-476": ["Mod.426"],          # Restriction orifices - lube oil
    "SOP-491": ["Mod.472"],          # Acoustic resonance BB3 long crossovers
    "SOP-505": ["Mod.481"],          # Non-metallic wear parts
    "SOP-506": ["Mod.482"],          # O-rings selection
    "SOP-520": ["Mod.496"],          # Preliminary rotor sizing
    "SOP-546": ["Mod.527"],          # Vaned channel and shroud thickness
    "SOP-556": ["Mod.541"],          # Pressure pulsations - design criterion
    "SOP-559": ["Mod.541"],          # Pressure Pulsation Calculation
    "SOP-569": ["Mod.546"],          # Casting wall thickness
    "SOP-570": ["Mod.547"],          # Restriction orifice calculation
    "SOP-579": ["Mod.555"],          # Estimating Design Hours
    "SOP-587": ["Mod.559"],          # Impeller peripheral speed
}

# Mapping inverso: Mod → SOP
MOD_TO_SOP = {}
for sop, mods in SOP_TO_MOD.items():
    for mod in mods:
        if mod not in MOD_TO_SOP:
            MOD_TO_SOP[mod] = []
        MOD_TO_SOP[mod].append(sop)


# ============================================================
# FUNZIONI PUBBLICHE
# ============================================================

def get_related_mods(sop_id: str) -> list:
    """Restituisce i Mod collegati a una SOP. Es: get_related_mods('SOP-521') → ['Mod.497']"""
    key = sop_id.upper().strip()
    if not key.startswith("SOP-"):
        key = f"SOP-{key}"
    return SOP_TO_MOD.get(key, [])


def get_related_sops(mod_id: str) -> list:
    """Restituisce le SOP collegate a un Mod. Es: get_related_sops('Mod.497') → ['SOP-521']"""
    key = mod_id.strip()
    if not key.startswith("Mod."):
        key = f"Mod.{key}"
    return MOD_TO_SOP.get(key, [])


def enrich_context_with_mappings(docs: list) -> str:
    """
    Analizza i documenti recuperati e genera una stringa di mapping
    SOP↔Mod da inserire nel prompt.
    
    Args:
        docs: Lista di documenti dal database vettoriale
    
    Returns:
        Stringa formattata con i mapping trovati (vuota se nessun mapping)
    """
    found_mappings = []
    seen = set()

    for d in docs:
        source = d.get("source", "")
        text = d.get("text", "")
        combined = f"{source} {text}"

        # Cerca SOP-xxx nel source o nel testo
        sop_matches = re.findall(r"SOP[-\s]?(\d{3,4})", combined, re.IGNORECASE)
        for num in sop_matches:
            sop_id = f"SOP-{num}"
            if sop_id in SOP_TO_MOD and sop_id not in seen:
                seen.add(sop_id)
                mods = SOP_TO_MOD[sop_id]
                found_mappings.append(f"- {sop_id} → usa {', '.join(mods)}")

        # Cerca Mod.xxx nel source o nel testo
        mod_matches = re.findall(r"Mod\.?\s*(\d{3,4})", combined, re.IGNORECASE)
        for num in mod_matches:
            mod_id = f"Mod.{num}"
            if mod_id in MOD_TO_SOP and mod_id not in seen:
                seen.add(mod_id)
                sops = MOD_TO_SOP[mod_id]
                found_mappings.append(f"- {mod_id} ← procedura in {', '.join(sops)}")

    return "\n".join(found_mappings)
