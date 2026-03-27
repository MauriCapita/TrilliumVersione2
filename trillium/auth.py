"""
Trillium RAG - Sistema di Autenticazione
Login basico con ruoli: viewer (consultazione) e admin (gestione completa).
"""

import hashlib
import json
import os
import streamlit as st

# ============================================================
# CONFIGURAZIONE
# ============================================================

_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")

# Ruoli disponibili
ROLE_VIEWER = "viewer"
ROLE_ADMIN = "admin"

# Pagine per ruolo
PAGES_VIEWER = ["Dashboard", "Stima Pesi", "Database Pompe", "Analisi Disegni", "Chat RAG", "Grafo Documenti", "TIFF Explorer", "Configurazione", "Trend Analysis", "Manuale"]
PAGES_ADMIN = ["Dashboard", "Stima Pesi", "Database Pompe", "Analisi Disegni", "Indicizza", "Chat RAG", "Confronta Modelli", "Grafo Documenti", "Analytics", "Doc Analytics", "TIFF Explorer", "Configurazione", "Trend Analysis", "Manuale"]


# ============================================================
# FUNZIONI HASH PASSWORD
# ============================================================

def _hash_password(password: str) -> str:
    """Hash SHA-256 della password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_users() -> list:
    """Carica gli utenti dal file users.json."""
    if not os.path.exists(_USERS_FILE):
        return []
    try:
        with open(_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("users", [])
    except (json.JSONDecodeError, IOError):
        return []


def _verify_credentials(username: str, password: str):
    """
    Verifica le credenziali e restituisce il dict utente se valido, None altrimenti.
    """
    users = _load_users()
    pwd_hash = _hash_password(password)
    for u in users:
        if u.get("username") == username and u.get("password_hash") == pwd_hash:
            return u
    return None


# ============================================================
# INTERFACCIA STREAMLIT
# ============================================================

def is_authenticated() -> bool:
    """Verifica se l'utente corrente è autenticato."""
    return st.session_state.get("authenticated", False)


def get_user_role() -> str:
    """Restituisce il ruolo dell'utente corrente (viewer/admin)."""
    return st.session_state.get("user_role", ROLE_VIEWER)


def get_user_name() -> str:
    """Restituisce il nome visualizzato dell'utente corrente."""
    return st.session_state.get("user_display_name", "")


def get_allowed_pages() -> list:
    """Restituisce le pagine consentite per il ruolo corrente."""
    if get_user_role() == ROLE_ADMIN:
        return PAGES_ADMIN
    return PAGES_VIEWER


def show_login_page():
    """Mostra la pagina di login professionale."""
    # Centra il form
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown("---")
        st.markdown("## Trillium V2 — Weight Estimation")
        st.markdown("Accedi per utilizzare il sistema di stima pesi.")
        st.markdown("")

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Inserisci username")
            password = st.text_input("Password", type="password", placeholder="Inserisci password")
            submitted = st.form_submit_button("Accedi", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Inserisci username e password.")
                else:
                    user = _verify_credentials(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_role = user.get("role", ROLE_VIEWER)
                        st.session_state.user_display_name = user.get("name", username)
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("Credenziali non valide.")

        st.markdown("---")
        st.caption("Contatta l'amministratore per ottenere le credenziali di accesso.")


def show_user_info_sidebar():
    """Mostra le informazioni utente nella sidebar."""
    role_label = "Amministratore" if get_user_role() == ROLE_ADMIN else "Consultazione"
    st.markdown(f"**Utente:** {get_user_name()}")
    st.caption(f"Ruolo: {role_label}")
    if st.button("Esci", key="logout_btn", use_container_width=True):
        for key in ["authenticated", "user_role", "user_display_name", "username"]:
            st.session_state.pop(key, None)
        st.rerun()


def check_auth():
    """
    Controlla autenticazione. Se non autenticato, mostra login e blocca.
    Se non esiste users.json, l'auth è disabilitata (accesso libero come admin).
    """
    # Se non esiste il file utenti, disabilita l'auth
    if not os.path.exists(_USERS_FILE):
        st.session_state.authenticated = True
        st.session_state.user_role = ROLE_ADMIN
        st.session_state.user_display_name = "Admin (no auth)"
        return

    if not is_authenticated():
        show_login_page()
        st.stop()
