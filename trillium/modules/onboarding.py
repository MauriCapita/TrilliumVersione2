"""
Trillium V2 — Onboarding Guidato
Wizard 3 step per nuovi utenti: spiega il sistema, fa fare una stima di prova,
mostra i risultati. Si mostra solo al primo accesso.
"""

import streamlit as st
import os

_ONBOARDING_FLAG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".onboarding_complete"
)


def is_onboarding_done() -> bool:
    """Controlla se l'onboarding è già stato completato."""
    if st.session_state.get("onboarding_done", False):
        return True
    if os.path.exists(_ONBOARDING_FLAG):
        st.session_state["onboarding_done"] = True
        return True
    return False


def mark_onboarding_done():
    """Segna l'onboarding come completato."""
    st.session_state["onboarding_done"] = True
    try:
        with open(_ONBOARDING_FLAG, "w") as f:
            f.write("done")
    except Exception:
        pass


def render_onboarding():
    """Render il wizard di onboarding."""

    # Inizializza step
    if "onboarding_step" not in st.session_state:
        st.session_state["onboarding_step"] = 1

    step = st.session_state["onboarding_step"]

    # Header
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #1B9C4F; margin-bottom: 5px;">🏭 Benvenuto in Trillium V2</h1>
        <p style="color: #64748B; font-size: 16px;">Sistema AI per la Stima Pesi Componenti Pompe</p>
    </div>
    """, unsafe_allow_html=True)

    # Progress bar
    st.progress(step / 3, text=f"Step {step} di 3")

    # ===========================================
    # STEP 1: Cos'è Trillium
    # ===========================================
    if step == 1:
        st.markdown("### 📖 Step 1 — Cos'è Trillium V2?")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
**Trillium V2** è un sistema AI che ti aiuta a **stimare il peso dei componenti
di pompe centrifughe** a partire dai parametri di progetto.

#### Come funziona:
1. 📁 **Indicizzi** i disegni tecnici storici (PDF, Excel, TIF)
2. ⚖️ **Inserisci** i parametri della pompa (famiglia, Nq, materiale...)
3. 🤖 **Il sistema calcola** il peso di ogni componente usando formule di scaling
4. 📊 **Confronta** con i dati reali estratti dai documenti

#### Pagine principali:
| Pagina | Cosa fa |
|--------|---------|
| **Stima Pesi** | Calcola il peso dei componenti |
| **Database Pompe** | Consulta componenti estratti dai disegni |
| **Analisi Disegni** | Verifica completezza dati nei documenti |
| **Chat RAG** | Fai domande in linguaggio naturale |
| **Indicizza** | Carica nuovi documenti nel sistema |
            """)

        with col2:
            st.markdown("""
#### Chi lo usa:
- 👷 **Project Engineer** — per preventivi e offerte
- 🔧 **Ufficio Tecnico** — per verifica pesi in fase di design
- 📋 **Procurement** — per stime di costo materiali

#### Prerequisiti:
- ✅ Database Qdrant attivo (documenti indicizzati)
- ✅ Chiave API OpenAI (per LLM e embedding)
- ✅ Documenti tecnici pompe (disegni, datasheet, parts list)

#### Famiglie pompe supportate:
- **OH** — Overhung (aspirazione assiale)
- **BB** — Between Bearings (cassa bipartita)
- **VS** — Vertical Suspended

> 💡 **Suggerimento:** Più documenti indicizzi, più accurate
> saranno le stime. Inizia con almeno 50-100 disegni.
            """)

        col_skip, col_next = st.columns([1, 1])
        with col_skip:
            if st.button("Salta onboarding →", use_container_width=True):
                mark_onboarding_done()
                st.rerun()
        with col_next:
            if st.button("Avanti — Prova una stima ▶", type="primary", use_container_width=True):
                st.session_state["onboarding_step"] = 2
                st.rerun()

    # ===========================================
    # STEP 2: Stima di prova
    # ===========================================
    elif step == 2:
        st.markdown("### ⚖️ Step 2 — Facciamo una stima di prova!")
        st.caption("ℹ️ Prova a compilare questi parametri per una pompa BB1 standard. "
                   "I valori sono pre-compilati come esempio — puoi modificarli.")

        col_form, col_info = st.columns([2, 1])

        with col_form:
            st.markdown("**Parametri esempio: Pompa BB1 — Carbon Steel — 10 bar**")

            c1, c2 = st.columns(2)
            with c1:
                demo_family = st.selectbox(
                    "Famiglia Pompa", ["BB1", "OH1", "OH2", "BB2", "VS1"],
                    index=0, key="demo_family",
                    help="BB1 = Axially Split, pompa a cassa bipartita monostadio",
                )
                demo_nq = st.number_input(
                    "Nq (velocità specifica)",
                    min_value=10.0, max_value=200.0, value=30.0, step=5.0,
                    key="demo_nq",
                    help="Default 30 = pompa radiale standard",
                )
            with c2:
                demo_material = st.selectbox(
                    "Materiale", ["Carbon Steel", "SS 316", "Duplex 2205"],
                    index=0, key="demo_material",
                    help="Carbon Steel è il più comune, SS 316 per corrosione",
                )
                demo_pressure = st.number_input(
                    "Pressione (bar)",
                    min_value=1.0, max_value=200.0, value=10.0, step=5.0,
                    key="demo_pressure",
                    help="10 bar = bassa pressione standard",
                )

        with col_info:
            st.markdown("#### 💡 Cosa succede?")
            st.markdown(f"""
Quando premi **Calcola**:
1. Il sistema seleziona il **template {demo_family}** (~22 componenti)
2. Per ogni componente applica le **formule di scaling**
3. Il materiale **{demo_material}** determina la densità
4. La pressione **{demo_pressure} bar** influenza gli spessori

**Risultato:** tabella con peso di ogni componente + totale.
            """)

        if st.button("🚀 Calcola Stima di Prova", type="primary", use_container_width=True):
            try:
                from weight_engine.estimator import run_estimation
                params = {
                    "pump_family": demo_family,
                    "nq": demo_nq,
                    "scale_factor": 1.0,
                    "num_stages": 1,
                    "pressure": demo_pressure,
                    "temperature": 20.0,
                    "material": demo_material,
                    "wall_thickness": 0,
                    "flange_rating": 150,
                    "suction_size": 8.0,
                    "discharge_size": 6.0,
                }
                with st.spinner("Calcolo in corso..."):
                    result = run_estimation(params)

                st.session_state["demo_result"] = result
                st.session_state["onboarding_step"] = 3
                st.rerun()

            except Exception as e:
                st.error(f"Errore nella stima: {e}")
                st.caption("Il motore di stima non è disponibile. Puoi saltare l'onboarding "
                           "e provare dalla pagina Stima Pesi.")

        col_back, col_skip2 = st.columns(2)
        with col_back:
            if st.button("← Indietro", use_container_width=True):
                st.session_state["onboarding_step"] = 1
                st.rerun()
        with col_skip2:
            if st.button("Salta onboarding →", use_container_width=True):
                mark_onboarding_done()
                st.rerun()

    # ===========================================
    # STEP 3: Risultati
    # ===========================================
    elif step == 3:
        st.markdown("### 📊 Step 3 — Ecco i risultati!")

        result = st.session_state.get("demo_result")
        if result:
            # KPI principali
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Peso Totale", f"{result.total_weight_kg:,.1f} kg")
            c2.metric("Componenti Stimati",
                       len([c for c in result.components if c.is_estimated]))
            c3.metric("Confidenza Alta",
                       len([c for c in result.components if c.confidence == "alta"]))
            c4.metric("Avvisi", len(result.warnings))

            # Tabella componenti (top 10)
            st.markdown("**Top 10 componenti per peso:**")
            estimated = sorted(
                [c for c in result.components if c.is_estimated and c.estimated_weight_kg],
                key=lambda c: c.estimated_weight_kg, reverse=True
            )[:10]

            for comp in estimated:
                conf_icon = "🟢" if comp.confidence == "alta" else "🟡" if comp.confidence == "media" else "🔴"
                st.caption(
                    f"{conf_icon} **{comp.component_name}** — "
                    f"{comp.estimated_weight_kg:.1f} kg — "
                    f"Gruppo: {comp.group} — "
                    f"Confidenza: {comp.confidence}"
                )

            st.markdown("---")
            st.markdown("#### 🎓 Come leggere i risultati:")
            st.markdown("""
| Elemento | Significato |
|----------|-------------|
| **Peso Totale** | Somma di tutti i componenti stimati |
| **Confidenza 🟢/🟡/🔴** | Alta = formula validata, Media = stima ragionevole, Bassa = approssimativa |
| **Gruppo** | Categoria del componente (Idraulica, Meccanica, Tenute, Cuscinetti...) |
| **Avvisi** | Parametri fuori range o incompatibilità rilevate |

> 💡 Per migliorare l'accuratezza: indicizza più disegni tecnici e usa
> il Confronto Configurazioni per verificare con materiali alternativi.
            """)
        else:
            st.warning("Nessun risultato di prova disponibile. Puoi fare una stima dalla pagina Stima Pesi.")

        st.markdown("---")
        if st.button("✅ Ho capito! Inizia ad usare Trillium", type="primary", use_container_width=True):
            mark_onboarding_done()
            # Pulisci session state demo
            for key in ["demo_result", "onboarding_step", "demo_family",
                         "demo_nq", "demo_material", "demo_pressure"]:
                st.session_state.pop(key, None)
            st.rerun()

        if st.button("← Torna indietro", use_container_width=True):
            st.session_state["onboarding_step"] = 2
            st.rerun()
