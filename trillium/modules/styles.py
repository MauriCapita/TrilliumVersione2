"""
Trillium V2 - Stili CSS e configurazione pagina
Design System ispirato a Bilancio Sostenibilità — elegante, professionale, green accent.

Palette:
  Primary Green:  hsl(142, 76%, 36%)  — #1B9C4F
  Secondary Blue: hsl(213, 94%, 68%)  — #5BA4F5
  Accent Orange:  hsl(25, 95%, 53%)   — #F58B13
  Background:     hsl(0, 0%, 98%)     — #FAFAFA
  Foreground:     hsl(215, 25%, 15%)  — #1C2536
  Muted:          hsl(210, 40%, 96%)  — #F0F4F8
  Border:         hsl(220, 13%, 91%)  — #E4E7EC
"""

import streamlit as st


def setup_page():
    """Configura la pagina Streamlit e inietta CSS premium."""
    st.set_page_config(
        page_title="Trillium V2 — AI Weight Estimation",
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("""
    <style>
        /* ============================================================
           FONT — System stack (come bilanciosostenibilità)
           ============================================================ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        body, .stApp, .stMarkdown, .stButton > button,
        .stSelectbox, .stTextInput, .stTextArea, .stNumberInput {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                         Roboto, 'Helvetica Neue', Arial, sans-serif !important;
        }

        /* ============================================================
           SFONDO PRINCIPALE — Bianco latte
           ============================================================ */
        .stApp {
            background: hsl(0, 0%, 98%);
        }
        .main .block-container {
            padding-top: 2rem;
        }

        /* ============================================================
           TITOLI — Scuri, eleganti
           ============================================================ */
        h1 {
            color: hsl(142, 76%, 36%) !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }
        h2, h3 {
            color: hsl(215, 25%, 15%) !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }
        h4, h5, h6 {
            color: hsl(215, 25%, 25%) !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em;
        }
        /* Testo contenuti — solo elementi visibili utente, NO span/label interni di Streamlit */
        .stMarkdown p,
        .stMarkdown li,
        .stMarkdown span,
        .element-container p,
        .stCaption p {
            color: hsl(215, 25%, 25%) !important;
        }

        /* DataFrame — NON toccare gli stili interni (popup, filtri, icone) */
        [data-testid="stDataFrame"] * {
            color: unset;
        }
        .stDataFrame iframe {
            color-scheme: light;
        }
        /* Popup/menu del dataframe — sfondo chiaro, testo scuro */
        [data-baseweb="popover"] *,
        [data-baseweb="menu"] *,
        [data-baseweb="select"] * {
            color: unset;
        }

        /* ============================================================
           PULSANTI — Verde sustainability, elegante
           ============================================================ */
        .stButton > button {
            width: 100%;
            border-radius: 12px;
            border: none;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 0.9rem;
            letter-spacing: 0.15px;
            text-transform: none;
            background: linear-gradient(135deg, hsl(142, 76%, 36%) 0%, hsl(142, 60%, 45%) 100%);
            color: hsl(0, 0%, 98%) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 6px -1px hsla(215, 25%, 15%, 0.1);
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, hsl(142, 76%, 32%) 0%, hsl(142, 60%, 40%) 100%);
            box-shadow: 0 10px 30px -10px hsla(142, 76%, 36%, 0.25);
            transform: translateY(-1px);
        }
        .stButton > button:active {
            transform: translateY(0);
        }

        /* ============================================================
           METRICHE — Card bianca con ombra elegante
           ============================================================ */
        [data-testid="stMetric"] {
            background: hsl(0, 0%, 100%);
            padding: 1.2rem;
            border-radius: 12px;
            border: 1px solid hsl(220, 13%, 91%);
            box-shadow: 0 4px 6px -1px hsla(215, 25%, 15%, 0.06);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        [data-testid="stMetric"]:hover {
            box-shadow: 0 10px 30px -10px hsla(142, 76%, 36%, 0.12);
        }
        [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
            font-weight: 700 !important;
            color: hsl(215, 25%, 15%) !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.7rem !important;
            color: hsl(215, 16%, 47%) !important;
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }
        [data-testid="stMetricDelta"] > div {
            font-weight: 600 !important;
        }

        /* ============================================================
           SIDEBAR — Pulita e professionale
           ============================================================ */
        [data-testid="stSidebar"] {
            background: hsl(210, 40%, 96%) !important;
            border-right: 1px solid hsl(220, 13%, 91%);
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: hsl(215, 25%, 15%) !important;
        }
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] .stMarkdown span {
            color: hsl(215, 16%, 47%) !important;
        }

        /* Radio menu — stato normale */
        [data-testid="stSidebar"] .stRadio label {
            font-weight: 500;
            color: hsl(215, 16%, 47%) !important;
            padding: 0.3rem 0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        [data-testid="stSidebar"] .stRadio label:hover {
            color: hsl(142, 76%, 36%) !important;
        }

        /* Radio dot selezionato — verde */
        [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] input:checked + div {
            border-color: hsl(142, 76%, 36%) !important;
            background: hsl(142, 76%, 36%) !important;
        }

        /* Label voce selezionata — SCURA ben leggibile */
        [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) label,
        [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p,
        [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) span,
        [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) div {
            color: hsl(215, 25%, 10%) !important;
            font-weight: 700 !important;
        }

        /* Testo sidebar — solo markdown visibile */
        [data-testid="stSidebar"] .stMarkdown p {
            color: hsl(215, 25%, 25%) !important;
        }

        /* Pulsanti sidebar — testo BIANCO chiaro */
        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(135deg, hsl(142, 76%, 36%) 0%, hsl(142, 60%, 50%) 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: 600;
            font-size: 0.9rem;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: linear-gradient(135deg, hsl(142, 76%, 30%) 0%, hsl(142, 60%, 42%) 100%) !important;
        }

        /* ============================================================
           EXPANDER — Bordi sottili, hover verde glow
           ============================================================ */
        .stExpander {
            border: 1px solid hsl(220, 13%, 91%) !important;
            border-radius: 12px !important;
            background: hsl(0, 0%, 100%) !important;
            overflow: hidden;
        }
        .stExpander:hover {
            border-color: hsl(220, 13%, 85%) !important;
            box-shadow: 0 4px 6px -1px hsla(215, 25%, 15%, 0.06);
        }
        .stExpander > details > summary > span {
            color: hsl(215, 25%, 15%) !important;
            font-weight: 500;
        }

        /* ============================================================
           INPUT / SELECT — Puliti con focus verde
           ============================================================ */
        .stSelectbox > div > div,
        .stNumberInput > div > div > input,
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border-radius: 12px !important;
            border: 1px solid hsl(220, 13%, 91%) !important;
            background: hsl(0, 0%, 100%) !important;
            color: hsl(215, 25%, 15%) !important;
        }
        .stSelectbox > div > div:focus-within,
        .stNumberInput > div > div > input:focus,
        .stTextInput > div > div > input:focus {
            border-color: hsl(142, 76%, 36%) !important;
            box-shadow: 0 0 0 2px hsla(142, 76%, 36%, 0.15) !important;
        }

        /* ============================================================
           DOWNLOAD BUTTON — Accent arancione
           ============================================================ */
        .stDownloadButton > button {
            background: linear-gradient(135deg, hsl(25, 95%, 53%) 0%, hsl(25, 90%, 60%) 100%) !important;
            color: hsl(0, 0%, 98%) !important;
            border: none !important;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px hsla(25, 95%, 53%, 0.2);
        }
        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, hsl(25, 95%, 48%) 0%, hsl(25, 90%, 55%) 100%) !important;
            box-shadow: 0 10px 30px -10px hsla(25, 95%, 53%, 0.25);
        }

        /* ============================================================
           PROGRESS BAR — Verde sustainability
           ============================================================ */
        .stProgress > div > div > div {
            background: linear-gradient(90deg,
                hsl(142, 76%, 36%),
                hsl(142, 60%, 55%),
                hsl(142, 50%, 70%)) !important;
            border-radius: 4px;
        }

        /* ============================================================
           CHAT — Bolle messaggi pulite
           ============================================================ */
        .stChatMessage {
            border-radius: 12px;
            margin-bottom: 0.75rem;
            border: 1px solid hsl(220, 13%, 91%);
            background: hsl(0, 0%, 100%);
        }

        /* ============================================================
           FORM
           ============================================================ */
        .stForm {
            border: 1px solid hsl(220, 13%, 91%);
            border-radius: 12px;
            padding: 2rem;
            background: hsl(0, 0%, 100%);
            box-shadow: 0 4px 6px -1px hsla(215, 25%, 15%, 0.06);
        }

        /* ============================================================
           TABELLE — Clean
           ============================================================ */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid hsl(220, 13%, 91%);
        }

        /* ============================================================
           CAPTION e testo secondario — Grigio muted
           ============================================================ */
        .stCaption, small, .stMarkdown small {
            color: hsl(215, 16%, 47%) !important;
        }

        /* ============================================================
           ALERT — Colori leggibili
           ============================================================ */
        .stAlert [data-testid="stNotificationContentSuccess"] {
            color: hsl(142, 76%, 28%) !important;
        }
        .stAlert [data-testid="stNotificationContentWarning"] {
            color: hsl(25, 85%, 40%) !important;
        }
        .stAlert [data-testid="stNotificationContentError"] {
            color: hsl(0, 84%, 45%) !important;
        }

        /* ============================================================
           SCROLLBAR — Elegante
           ============================================================ */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: hsl(210, 40%, 96%); }
        ::-webkit-scrollbar-thumb { background: hsl(220, 13%, 82%); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: hsl(215, 16%, 65%); }

        /* ============================================================
           DIVIDER
           ============================================================ */
        hr { border-color: hsl(220, 13%, 91%) !important; }

        /* ============================================================
           MICRO-ANIMAZIONI — Smooth cubic-bezier
           ============================================================ */
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stMetric"],
        .stExpander,
        .stSelectbox > div > div {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
    </style>
    """, unsafe_allow_html=True)
