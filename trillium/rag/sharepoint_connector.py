"""
Modulo per connettersi a SharePoint/OneDrive e scaricare file
Supporta autenticazione OAuth2 con Microsoft Graph API
"""

import os
import re
import tempfile
import requests
from typing import List, Tuple, Optional
from urllib.parse import urlparse, parse_qs, unquote
from msal import ConfidentialClientApplication, PublicClientApplication
from rich import print
import shutil


# ============================================================
# CONFIGURAZIONE
# ============================================================

# Microsoft Graph API endpoints
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
GRAPH_API_SCOPE = ["https://graph.microsoft.com/Files.Read.All", "https://graph.microsoft.com/Sites.Read.All"]

# Configurazione app Azure AD (può essere configurata via .env)
CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET", "")
TENANT_ID = os.getenv("SHAREPOINT_TENANT_ID", "")

# Se non c'è client_secret, usa PublicClientApplication (device code flow)
USE_PUBLIC_CLIENT = not bool(CLIENT_SECRET)


# ============================================================
# PARSING URL SHAREPOINT/ONEDRIVE
# ============================================================

def parse_sharepoint_url(url: str) -> Optional[dict]:
    """
    Estrae informazioni da un URL SharePoint/OneDrive.
    
    Supporta formati:
    - https://[tenant]-my.sharepoint.com/personal/[user]/_layouts/15/onedrive.aspx?id=...
    - https://[tenant].sharepoint.com/personal/[user]/_layouts/15/onedrive.aspx?...
    - https://[tenant].sharepoint.com/sites/[site]/Shared%20Documents/...
    
    Returns:
        dict con: type, site_url, user/site_name, folder_path, original_url
    """
    try:
        parsed = urlparse(url)
        
        # Estrai parametri dalla query string
        query_params = parse_qs(parsed.query)
        
        # Cerca ID nella query string (parametro "id" contiene il percorso)
        folder_id = query_params.get("id", [None])[0]
        if folder_id:
            folder_id = unquote(folder_id)
            # Rimuovi il prefisso /personal/[user]/ se presente
            if folder_id.startswith("/personal/"):
                parts = folder_id.split("/")
                if len(parts) >= 3:
                    folder_id = "/" + "/".join(parts[2:])  # Rimuovi /personal/[user]
        
        # Estrai path dal percorso
        path_parts = [p for p in parsed.path.split("/") if p]
        
        # Identifica il tipo di URL
        if "onedrive.aspx" in parsed.path or "-my.sharepoint.com" in parsed.netloc:
            # OneDrive personale
            if "personal" in path_parts:
                user_idx = path_parts.index("personal")
                if user_idx + 1 < len(path_parts):
                    user = path_parts[user_idx + 1]
                    
                    # Costruisci site URL (rimuovi -my dal tenant)
                    tenant = parsed.netloc.split(".")[0]
                    if tenant.endswith("-my"):
                        tenant = tenant[:-3]
                    site_url = f"https://{tenant}.sharepoint.com"
                    
                    # Usa folder_id se disponibile, altrimenti default
                    folder_path = folder_id if folder_id else "/Documents"
                    
                    return {
                        "type": "onedrive_personal",
                        "site_url": site_url,
                        "user": user,
                        "folder_path": folder_path,
                        "original_url": url
                    }
        
        elif "sharepoint.com" in parsed.netloc and "sites" in path_parts:
            # SharePoint site
            site_idx = path_parts.index("sites")
            if site_idx + 1 < len(path_parts):
                site_name = path_parts[site_idx + 1]
                tenant = parsed.netloc.split(".")[0]
                site_url = f"https://{tenant}.sharepoint.com/sites/{site_name}"
                
                # Estrai path del documento
                doc_path = "/" + "/".join(path_parts[site_idx + 2:]) if site_idx + 2 < len(path_parts) else "/"
                
                return {
                    "type": "sharepoint_site",
                    "site_url": site_url,
                    "site_name": site_name,
                    "folder_path": doc_path,
                    "original_url": url
                }
        
        # Se non riconosciuto, prova a estrarre informazioni generiche
        if "sharepoint.com" in parsed.netloc:
            return {
                "type": "unknown",
                "site_url": f"https://{parsed.netloc.split('/')[0]}",
                "folder_path": folder_id if folder_id else parsed.path,
                "original_url": url
            }
        
        return None
        
    except Exception as e:
        print(f"[red]Errore parsing URL SharePoint: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


# ============================================================
# AUTENTICAZIONE
# ============================================================

def get_access_token() -> Optional[str]:
    """
    Ottiene un access token per Microsoft Graph API.
    
    Supporta:
    - ConfidentialClientApplication (con client_secret)
    - PublicClientApplication (device code flow)
    """
    if not CLIENT_ID:
        # Usa autenticazione interattiva con client ID pubblico
        return get_access_token_interactive()
    
    if USE_PUBLIC_CLIENT:
        # Public client (device code flow)
        app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}" if TENANT_ID else "https://login.microsoftonline.com/common"
        )
        
        # Prova a ottenere token dalla cache
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(GRAPH_API_SCOPE, account=accounts[0])
            if result and "access_token" in result:
                return result["access_token"]
        
        # Autenticazione interattiva del browser (più user-friendly)
        print("[cyan]🔐 Apertura browser per autenticazione...[/cyan]")
        print("[yellow]Inserisci le tue credenziali nel browser quando richiesto[/yellow]\n")
        
        result = app.acquire_token_interactive(
            scopes=GRAPH_API_SCOPE,
            prompt="select_account",
        )
        
        if "access_token" in result:
            print("[green]✓ Autenticazione completata[/green]")
            return result["access_token"]
        else:
            error_msg = result.get('error_description', result.get('error', 'Unknown error'))
            print(f"[red]Errore autenticazione: {error_msg}[/red]")
            
            # Fallback a device code flow se l'autenticazione interattiva fallisce
            print("\n[yellow]Tentativo con device code flow...[/yellow]")
            flow = app.initiate_device_flow(scopes=GRAPH_API_SCOPE)
            
            if "user_code" not in flow:
                print(f"[red]Errore inizializzazione device flow: {flow.get('error_description', 'Unknown error')}[/red]")
                return None
            
            print(f"\n[bold]Apri questo URL nel browser:[/bold] {flow['verification_uri']}")
            print(f"[bold]Inserisci questo codice:[/bold] {flow['user_code']}\n")
            
            result = app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                print("[green]✓ Autenticazione completata[/green]")
                return result["access_token"]
            else:
                print(f"[red]Errore autenticazione: {result.get('error_description', 'Unknown error')}[/red]")
                return None
    else:
        # Confidential client (client credentials flow)
        if not CLIENT_SECRET or not TENANT_ID:
            print("[red]CLIENT_SECRET e TENANT_ID richiesti per autenticazione app-only[/red]")
            return None
        
        app = ConfidentialClientApplication(
            client_id=CLIENT_ID,
            client_credential=CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}"
        )
        
        result = app.acquire_token_for_client(scopes=GRAPH_API_SCOPE)
        
        if "access_token" in result:
            return result["access_token"]
        else:
            print(f"[red]Errore autenticazione: {result.get('error_description', 'Unknown error')}[/red]")
            return None


def get_access_token_interactive() -> Optional[str]:
    """
    Autenticazione interattiva del browser quando non ci sono credenziali configurate.
    Apre il browser per inserire le credenziali direttamente.
    """
    print("[cyan]🔐 Autenticazione interattiva del browser[/cyan]")
    print("[dim]Il browser si aprirà automaticamente per inserire le tue credenziali[/dim]\n")
    
    # Prova diversi client ID pubblici che funzionano meglio con tenant aziendali
    # Il primo è Microsoft Graph Explorer, il secondo è Azure CLI che funziona meglio
    public_client_ids = [
        "1950a258-227b-4e31-a9cf-717495945fc2",  # Microsoft Azure CLI (funziona meglio con tenant aziendali)
        "14d82eec-204b-4c2f-b95e-625a1e65c4c2",  # Microsoft Graph Explorer
    ]
    
    # Chiedi all'utente se vuole usare un client ID personalizzato
    print("[yellow]⚠ Per tenant aziendali, potrebbe essere necessario registrare un'app in Azure AD.[/yellow]")
    print("[dim]Vuoi inserire un CLIENT_ID personalizzato? (lascia vuoto per usare client ID pubblici)[/dim]")
    
    try:
        custom_client_id = input("CLIENT_ID (opzionale, premi Enter per saltare): ").strip()
        if custom_client_id:
            public_client_ids.insert(0, custom_client_id)
            print(f"[green]✓ Userò il client ID personalizzato[/green]\n")
    except (EOFError, KeyboardInterrupt):
        print("\n[yellow]Uso client ID pubblici di default[/yellow]\n")
    
    # Prova con i client ID disponibili
    for idx, public_client_id in enumerate(public_client_ids):
        try:
            print(f"[cyan]Tentativo {idx + 1}/{len(public_client_ids)} con client ID {public_client_id[:8]}...[/cyan]")
            
            app = PublicClientApplication(
                client_id=public_client_id,
                authority="https://login.microsoftonline.com/common"
            )
            
            # Prova prima a ottenere token dalla cache
            accounts = app.get_accounts()
            if accounts:
                result = app.acquire_token_silent(GRAPH_API_SCOPE, account=accounts[0])
                if result and "access_token" in result:
                    print("[green]✓ Token trovato in cache - autenticazione non necessaria[/green]")
                    return result["access_token"]
            
            # Autenticazione interattiva del browser
            print("[cyan]Apertura browser per autenticazione...[/cyan]")
            print("[yellow]Inserisci le tue credenziali nel browser quando richiesto[/yellow]\n")
            
            # Usa acquire_token_interactive che apre il browser automaticamente
            result = app.acquire_token_interactive(
                scopes=GRAPH_API_SCOPE,
                prompt="select_account",  # Mostra sempre la selezione account
            )
            
            if "access_token" in result:
                print("[green]✓ Autenticazione completata con successo![/green]")
                return result["access_token"]
            else:
                error_msg = result.get('error_description', result.get('error', 'Unknown error'))
                
                # Se è un errore di tenant/app non trovata, prova il prossimo client ID
                if "AADSTS700016" in error_msg or "not found in the directory" in error_msg:
                    print(f"[yellow]⚠ Client ID non disponibile in questo tenant. Provo il prossimo...[/yellow]\n")
                    continue
                
                print(f"[red]Errore autenticazione: {error_msg}[/red]")
                
                if "AADSTS65005" in error_msg or "consent" in error_msg.lower():
                    print("\n[yellow]⚠ L'applicazione richiede il consenso dell'amministratore.[/yellow]")
                    print("[yellow]Contatta l'amministratore IT per autorizzare l'applicazione.[/yellow]")
                elif "AADSTS70011" in error_msg:
                    print("\n[yellow]⚠ I permessi richiesti non sono disponibili per questo client ID.[/yellow]")
                    print("[yellow]Registra la tua app in Azure AD e configura SHAREPOINT_CLIENT_ID nel .env[/yellow]")
                
                # Se non è un errore di tenant, non provare altri client ID
                break
                
        except Exception as e:
            error_str = str(e)
            if "AADSTS700016" in error_str or "not found in the directory" in error_str:
                print(f"[yellow]⚠ Client ID non disponibile. Provo il prossimo...[/yellow]\n")
                continue
            print(f"[red]Errore durante autenticazione: {e}[/red]")
            continue
    
    # Se tutti i client ID falliscono
    print("\n[red]❌ Impossibile autenticarsi con i client ID disponibili.[/red]")
    print("\n[yellow]Soluzione: Registra la tua app in Azure AD[/yellow]")
    print("1. Vai su https://portal.azure.com → Azure Active Directory → App registrations")
    print("2. Crea una nuova registrazione (nome qualsiasi, es. 'Trillium SharePoint')")
    print("3. Nella sezione 'Authentication':")
    print("   - Aggiungi una piattaforma: 'Mobile and desktop applications'")
    print("   - Seleziona: 'https://login.microsoftonline.com/common/oauth2/nativeclient'")
    print("4. Nella sezione 'API permissions':")
    print("   - Aggiungi: Files.Read.All (Microsoft Graph) - Delegated")
    print("   - Aggiungi: Sites.Read.All (Microsoft Graph) - Delegated")
    print("5. Configura nel file .env:")
    print("   SHAREPOINT_CLIENT_ID=<il Client ID della tua app>")
    print("   SHAREPOINT_TENANT_ID=<il tuo Tenant ID, opzionale>")
    print("\n[cyan]Dopo la configurazione, riprova![/cyan]")
    return None


# ============================================================
# API MICROSOFT GRAPH
# ============================================================

def get_site_id(site_url: str, access_token: str) -> Optional[str]:
    """Ottiene l'ID del sito SharePoint"""
    try:
        # Normalizza site_url
        if not site_url.startswith("http"):
            site_url = f"https://{site_url}"
        
        # Usa l'API per ottenere il sito
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{GRAPH_API_ENDPOINT}/sites/{site_url.replace('https://', '').replace('http://', '')}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json().get("id")
        else:
            print(f"[yellow]⚠ Impossibile ottenere site ID: {response.status_code}[/yellow]")
            return None
    except Exception as e:
        print(f"[red]Errore ottenendo site ID: {e}[/red]")
        return None


def get_drive_id(site_id: str, access_token: str, drive_name: str = "Documents") -> Optional[str]:
    """Ottiene l'ID del drive (document library)"""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{GRAPH_API_ENDPOINT}/sites/{site_id}/drives",
            headers=headers
        )
        
        if response.status_code == 200:
            drives = response.json().get("value", [])
            for drive in drives:
                if drive.get("name") == drive_name:
                    return drive.get("id")
            # Se non trovato, usa il primo drive
            if drives:
                return drives[0].get("id")
        return None
    except Exception as e:
        print(f"[red]Errore ottenendo drive ID: {e}[/red]")
        return None


def get_user_drive_id(user: str, access_token: str) -> Optional[str]:
    """Ottiene l'ID del drive OneDrive personale"""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Prima prova con /me/drive (funziona se l'utente autenticato è il proprietario)
        response = requests.get(
            f"{GRAPH_API_ENDPOINT}/me/drive",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json().get("id")
        
        # Se fallisce, prova con /users/{user}/drive
        # Nota: user potrebbe essere in formato "user@domain.com" o "user_domain_com"
        # Converti formato se necessario
        if "_" in user and "@" not in user:
            # Converti formato: marco_frignani_alveo_it -> marco.frignani@alveo.it
            parts = user.split("_")
            if len(parts) >= 2:
                # Prova diversi formati
                user_formats = [
                    user,  # Formato originale
                    f"{parts[0]}.{'.'.join(parts[1:])}@alveo.it",  # Formato email
                    f"{user}@alveogroup.onmicrosoft.com",  # Formato tenant
                ]
            else:
                user_formats = [user]
        else:
            user_formats = [user]
        
        for user_format in user_formats:
            response = requests.get(
                f"{GRAPH_API_ENDPOINT}/users/{user_format}/drive",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json().get("id")
        
        return None
    except Exception as e:
        print(f"[red]Errore ottenendo user drive ID: {e}[/red]")
        return None


def list_folder_items(drive_id: str, folder_path: str, access_token: str) -> List[dict]:
    """
    Lista tutti i file in una cartella SharePoint/OneDrive.
    
    Returns:
        Lista di dict con: name, id, webUrl, mimeType, size
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Normalizza folder_path
        if folder_path.startswith("/"):
            folder_path = folder_path[1:]
        
        # Costruisci URL
        if folder_path and folder_path != "/":
            url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{folder_path}:/children"
        else:
            url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/root/children"
        
        all_items = []
        next_link = url
        
        while next_link:
            response = requests.get(next_link, headers=headers)
            
            if response.status_code != 200:
                print(f"[red]Errore listando cartella: {response.status_code} - {response.text}[/red]")
                break
            
            data = response.json()
            items = data.get("value", [])
            all_items.extend(items)
            
            # Controlla se ci sono più pagine
            next_link = data.get("@odata.nextLink")
        
        return all_items
        
    except Exception as e:
        print(f"[red]Errore listando cartella: {e}[/red]")
        return []


def download_file(drive_id: str, item_id: str, access_token: str, output_path: str) -> bool:
    """
    Scarica un file da SharePoint/OneDrive.
    
    Returns:
        True se successo, False altrimenti
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Ottieni download URL
        response = requests.get(
            f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{item_id}/content",
            headers=headers,
            stream=True
        )
        
        if response.status_code == 200:
            # Salva file
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"[red]Errore download file {item_id}: {response.status_code}[/red]")
            return False
            
    except Exception as e:
        print(f"[red]Errore download file: {e}[/red]")
        return False


# ============================================================
# FUNZIONE PRINCIPALE: SCARICA CARTELLA SHAREPOINT
# ============================================================

def download_sharepoint_folder(sharepoint_url: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    Scarica tutti i file da una cartella SharePoint/OneDrive in una cartella temporanea.
    
    Args:
        sharepoint_url: URL della cartella SharePoint/OneDrive
        output_dir: Directory dove salvare i file (opzionale, usa temp se None)
    
    Returns:
        Path della cartella locale con i file scaricati, o None se errore
    """
    print(f"[cyan]📥 Connessione a SharePoint/OneDrive: {sharepoint_url}[/cyan]")
    
    # Parse URL
    url_info = parse_sharepoint_url(sharepoint_url)
    if not url_info:
        print("[red]URL SharePoint/OneDrive non valido[/red]")
        return None
    
    # Ottieni access token
    access_token = get_access_token()
    if not access_token:
        print("[red]Impossibile ottenere access token[/red]")
        return None
    
    # Crea directory temporanea
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix="sharepoint_download_")
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    print(f"[cyan]📁 Salvataggio file in: {output_dir}[/cyan]")
    
    try:
        # Gestisci diversi tipi di URL
        if url_info["type"] == "onedrive_personal":
            # OneDrive personale
            # Prova prima con /me/drive (più affidabile)
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{GRAPH_API_ENDPOINT}/me/drive", headers=headers)
            
            if response.status_code == 200:
                drive_id = response.json().get("id")
            else:
                # Fallback: prova con user specifico
                user = url_info["user"]
                drive_id = get_user_drive_id(user, access_token)
            
            if not drive_id:
                print("[red]Impossibile ottenere drive ID per OneDrive personale[/red]")
                print(f"[yellow]Tentativo con user: {url_info.get('user', 'N/A')}[/yellow]")
                return None
            
            folder_path = url_info.get("folder_path", "/Documents")
            # Normalizza folder_path
            if folder_path.startswith("/"):
                folder_path = folder_path[1:]
            if not folder_path:
                folder_path = "Documents"
        
        elif url_info["type"] == "sharepoint_site":
            # SharePoint site
            site_id = get_site_id(url_info["site_url"], access_token)
            if not site_id:
                print("[red]Impossibile ottenere site ID[/red]")
                return None
            
            drive_id = get_drive_id(site_id, access_token)
            if not drive_id:
                print("[red]Impossibile ottenere drive ID[/red]")
                return None
            
            folder_path = url_info.get("folder_path", "/")
        
        else:
            print(f"[yellow]⚠ Tipo URL non supportato: {url_info['type']}[/yellow]")
            return None
        
        # Lista file nella cartella
        items = list_folder_items(drive_id, folder_path, access_token)
        
        if not items:
            print("[yellow]⚠ Nessun file trovato nella cartella[/yellow]")
            return output_dir
        
        # Filtra solo file (non cartelle)
        files = [item for item in items if "folder" not in item]
        
        print(f"[green]✓ Trovati {len(files)} file da scaricare[/green]")
        
        # Scarica ogni file
        downloaded = 0
        for item in files:
            item_name = item.get("name", "unknown")
            item_id = item.get("id")
            
            if not item_id:
                continue
            
            # Estrai estensione
            ext = os.path.splitext(item_name)[1].lower()
            supported_exts = (".pdf", ".tif", ".tiff", ".txt", ".xlsx", ".xls", ".xlsm", ".docx", ".doc", 
                            ".bmp", ".png", ".heic", ".heif", ".log")
            
            if not ext or ext not in supported_exts:
                print(f"[dim]⏭ Salto {item_name} (formato non supportato)[/dim]")
                continue
            
            output_path = os.path.join(output_dir, item_name)
            
            if download_file(drive_id, item_id, access_token, output_path):
                downloaded += 1
                print(f"[green]✓ Scaricato: {item_name}[/green]")
            else:
                print(f"[red]✗ Errore scaricando: {item_name}[/red]")
        
        print(f"[green]✔ Completato: {downloaded}/{len(files)} file scaricati[/green]")
        return output_dir
        
    except Exception as e:
        print(f"[red]Errore durante download: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


# ============================================================
# FUNZIONE RICORSIVA PER CARTELLE ANNIDATE
# ============================================================

def download_sharepoint_folder_recursive(sharepoint_url: str, output_dir: Optional[str] = None, max_depth: int = 5) -> Optional[str]:
    """
    Scarica ricorsivamente tutti i file da una cartella SharePoint/OneDrive.
    
    Args:
        sharepoint_url: URL della cartella SharePoint/OneDrive
        output_dir: Directory dove salvare i file
        max_depth: Massima profondità di ricorsione
    
    Returns:
        Path della cartella locale con i file scaricati
    """
    # Per ora usa la versione non ricorsiva
    # TODO: Implementare ricorsione se necessario
    return download_sharepoint_folder(sharepoint_url, output_dir)
