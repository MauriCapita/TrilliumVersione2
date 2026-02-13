# Proposta di riorganizzazione – Technical Documentation Project

## Problemi attuali (findability)

| Problema | Effetto |
|----------|---------|
| **Tutto in R&D vs RDE** | Per trovare "tutte le SOP" o "tutti i tool CFD" bisogna cercare in due cartelle. |
| **Nessuna separazione per tipo** | Mod (tool), SOP (procedure), G.xx (design) e checklist sono mescolati. |
| **Nessuna separazione per argomento** | Rotordynamics, CFD, gasket, bearing, NPSH sono sparsi. |
| **Nomi lunghi + ID** | I suffissi numerici (_848491, _929208) non aiutano la ricerca per tema. |
| **Nessun indice** | Con 164+ file non c’è un punto unico per capire “cosa c’è e dove”. |

---

## Opzione A – Organizzazione per **tipo di documento** (consigliata per uso quotidiano)

Obiettivo: rispondere a “dove sono le procedure?” / “dove sono i calcolatori?” in un colpo solo.

```
Technical Documentation Project/
├── 00_INDEX.md                    ← Indice navigabile (nuovo)
├── External/
│   ├── Standards/                 (già: International standard)
│   ├── Literature/
│   └── Papers/
│
└── Internal/
    ├── SOP/                       ← Tutte le procedure (PDF/DOCX) da R&D + RDE
    │   ├── Rotordynamics/         (opzionale: sottotema)
    │   ├── CFD/
    │   ├── Hydraulics/
    │   ├── Mechanical/            (bearing, gasket, bolt, shaft…)
    │   └── _other/
    │
    ├── Mod/                       ← Tutti i tool di calcolo (xlsm, xlsx, py)
    │   ├── Rotordynamics/
    │   ├── CFD_Hydraulics/
    │   ├── Mechanical/
    │   └── _other/
    │
    └── Design/                    ← Documenti G.xx, SA.xx, checklist
        └── (G.05.02.16, G.10.00.xx, Mod.529 checklist…)
```

**Vantaggi:**  
- Cerchi tutte le SOP in `Internal/SOP/`, tutti i Mod in `Internal/Mod/`.  
- Le sottocartelle per tema (Rotordynamics, CFD, Mechanical) permettono di restringere senza cercare in due reparti.

**Svantaggio:**  
- Si perde il “confine” R&D vs RDE (si può recuperare con tag nell’indice o nel nome, es. prefisso `RDE-` / `R&D-` se serve).

---

## Opzione B – Organizzazione per **dominio/argomento**

Obiettivo: rispondere a “tutto quello che riguarda CFD” o “tutto su bearing/gasket” in un’unica cartella.

```
Technical Documentation Project/
├── 00_INDEX.md
├── External/
│   └── (come sopra)
│
└── Internal/
    ├── Rotordynamics/             SOP + Mod su critical speed, torsionale, FRA, lateral…
    ├── CFD/                       SOP + Mod su pre/post processor, NPSH, blade passage…
    ├── Hydraulics/                NPSHr, MCSF, thrust (axial/radial), performance, trimming…
    ├── Mechanical_Structural/     Bearing, gasket, bolt/stud, shaft, barrel, hydrotest…
    ├── Design_Config/             BB5 configurator, design hours, checklist motori/strumenti…
    └── Other/
```

**Vantaggi:**  
- Per un progetto “rotordynamics” o “CFD” hai tutto in un posto.  
- Utile per onboarding (“leggi la cartella CFD”) o per RAG/search per dominio.

**Svantaggio:**  
- Alcuni documenti sono trasversali (es. una SOP che tocca sia idraulica che strutturale); serve una cartella `Other` o un indice che li citi in più sezioni.

---

## Opzione C – Migliorare **senza spostare** (indice solo)

Se non vuoi (ancora) spostare file:

- Aggiungere **un solo file `00_INDEX.md`** nella root di *Technical Documentation Project* con:
  - Elenco di tutte le SOP per numero (SOP-452, SOP-457, …) con titolo e path relativo.
  - Elenco di tutti i Mod con titolo e path.
  - Sezione “per tema” (es. “Rotordynamics: SOP-452, SOP-457, SOP-460, Mod.407, Mod.408, …”).

Così la findability migliora da subito (Ctrl+F sull’indice) senza toccare la struttura attuale. In un secondo momento si può applicare Opzione A o B e aggiornare l’indice.

---

## Raccomandazione

1. **Subito:** creare **`00_INDEX.md`** (Opzione C) con elenchi per tipo e per tema.  
2. **Poi:** adottare **Opzione A** (per tipo: SOP / Mod / Design) con sottocartelle per tema (Rotordynamics, CFD, Mechanical, …).  
3. **Naming:** mantenere i nomi attuali (Mod.xxx, SOP-xxx, Rev, ID) per tracciabilità; eventualmente aggiungere **short name** o **tag** solo nell’indice (es. `[CFD]`, `[RDE]`).

Se vuoi, il passo successivo può essere:  
- generare lo scheletro di `00_INDEX.md` con l’elenco reale dei file, oppure  
- definire la mappa esatta “questo file → questa cartella” per l’Opzione A (o B) così da poter automatizzare lo spostamento con uno script.
