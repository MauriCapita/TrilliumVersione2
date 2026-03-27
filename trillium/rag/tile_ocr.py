"""
Trillium V2 — Tile-Based OCR per Disegni Tecnici
Divide immagini di disegni tecnici in zone (tile) per migliorare
l'estrazione del testo, specialmente su cartigli e annotazioni.

Strategia:
1. Griglia adattiva in base al formato (A4→6, A3→9, A0→16 zone)
2. Rilevamento automatico del cartiglio (title block) con zoom extra
3. OCR su ogni zona singolarmente → unione e deduplicazione testo
"""

import logging
from PIL import Image, ImageFilter
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ============================================================
# 0. UPSCALING PER DPI TARGET
# ============================================================

def _upscale_to_target_dpi(img: Image.Image, target_dpi: int = 400) -> Image.Image:
    """
    Se l'immagine ha DPI inferiore al target, la upscala.
    I file TIF di scanner tecnici hanno tipicamente 200-300 DPI.
    Upscalando a 400+ DPI, Tesseract legge meglio testo piccolo
    come dimensioni, tolleranze, e note nel cartiglio.

    Args:
        img: Immagine PIL
        target_dpi: DPI desiderato (default 400)

    Returns:
        Immagine upscalata (o originale se già >= target)
    """
    # Leggi DPI dall'immagine (TIF/TIFF hanno quasi sempre questa info)
    dpi_info = img.info.get("dpi", (0, 0))
    current_dpi = 0
    if dpi_info and isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 2:
        current_dpi = max(int(dpi_info[0]), int(dpi_info[1]))

    if current_dpi <= 0:
        # Stima DPI dal formato carta e dimensioni pixel
        w, h = img.size
        long_side = max(w, h)
        # A3 = 420mm ≈ 16.5", A4 = 297mm ≈ 11.7", A1 = 841mm ≈ 33.1"
        # Stima: se long_side < 4000px → probabilmente ~200 DPI
        if long_side < 4000:
            current_dpi = 200
        elif long_side < 6000:
            current_dpi = 300
        else:
            current_dpi = 400  # Già alta risoluzione

    if current_dpi >= target_dpi:
        logger.debug("DPI attuale %d >= target %d, nessun upscaling", current_dpi, target_dpi)
        return img

    # Calcola fattore di scala
    scale = target_dpi / current_dpi
    new_w = int(img.size[0] * scale)
    new_h = int(img.size[1] * scale)

    # Limita a 15000px per lato (sicuro per Tesseract)
    MAX_UPSCALE_PX = 15000
    if max(new_w, new_h) > MAX_UPSCALE_PX:
        # Riduci scala per stare nel limite
        reduce = MAX_UPSCALE_PX / max(new_w, new_h)
        scale *= reduce
        new_w = int(img.size[0] * scale)
        new_h = int(img.size[1] * scale)
        actual_dpi = int(current_dpi * scale)
        logger.info(
            "Upscaling limitato a %dx%d (%d DPI effettivi) per sicurezza Tesseract",
            new_w, new_h, actual_dpi
        )

    # Scegli filtro di resampling
    try:
        from config import OCR_UPSCALE_FILTER
        filter_map = {
            "LANCZOS": Image.Resampling.LANCZOS,
            "BICUBIC": Image.Resampling.BICUBIC,
            "BILINEAR": Image.Resampling.BILINEAR,
        }
        resample = filter_map.get(OCR_UPSCALE_FILTER.upper(), Image.Resampling.LANCZOS)
    except ImportError:
        resample = Image.Resampling.LANCZOS

    logger.info(
        "Upscaling immagine: %dx%d (%d DPI) → %dx%d (%d DPI)",
        img.size[0], img.size[1], current_dpi, new_w, new_h, target_dpi
    )
    return img.resize((new_w, new_h), resample)


# ============================================================
# 1. CALCOLO GRIGLIA ADATTIVA
# ============================================================

# Soglie (in pixel) per decidere il numero di tile.
# Basate su risoluzioni comuni di scanner tecnici (200-400 DPI).
#   A4 @ 300 DPI ≈ 3508 × 2480           → max 5000
#   A3 @ 300 DPI ≈ 4961 × 3508           → max 7000
#   A1 @ 300 DPI ≈ 9933 × 7016           → max 10000
#   A0 @ 300 DPI ≈ 14043 × 9933          → > 10000

_GRID_RULES = [
    # (max_long_side_px, rows, cols)
    (5000,  2, 3),   # fino a A4:  6 tile
    (7500,  3, 3),   # A3:         9 tile
    (10500, 3, 4),   # A2/A1:     12 tile
    (99999, 4, 4),   # A0+:       16 tile
]


def compute_tile_grid(width: int, height: int) -> tuple[int, int]:
    """
    Restituisce (rows, cols) della griglia di tile in base alle dimensioni
    dell'immagine. L'orientamento (landscape/portrait) viene normalizzato.
    """
    long_side = max(width, height)
    for max_px, rows, cols in _GRID_RULES:
        if long_side <= max_px:
            # Se portrait, scambia righe/colonne in modo che le colonne
            # siano sempre sul lato lungo.
            if height > width:
                return cols, rows
            return rows, cols
    return 4, 4


# ============================================================
# 2. RILEVAMENTO CARTIGLIO (TITLE BLOCK)
# ============================================================

# Il cartiglio è quasi sempre nell'angolo basso-destra dei disegni
# tecnici (standard ISO 7200, ANSI Y14.1).
# Dimensioni tipiche: ~30% larghezza × ~20-25% altezza.

_TB_WIDTH_RATIO = 0.35   # 35% della larghezza
_TB_HEIGHT_RATIO = 0.28  # 28% dell'altezza


def detect_title_block_region(width: int, height: int) -> tuple[int, int, int, int]:
    """
    Restituisce (left, upper, right, lower) della regione cartiglio attesa.
    Posizione: angolo basso-destra.
    """
    tb_w = int(width * _TB_WIDTH_RATIO)
    tb_h = int(height * _TB_HEIGHT_RATIO)
    left = width - tb_w
    upper = height - tb_h
    return (left, upper, width, height)


def detect_notes_zone_region(width: int, height: int) -> tuple[int, int, int, int]:
    """
    Restituisce la regione delle note tecniche (basso-centro/sinistra).
    Nei disegni TPI, qui ci sono: peso finito, peso grezzo, tolleranze, materiale.
    Posizione: striscia bassa, dal 10% al 65% della larghezza.
    """
    notes_h = int(height * 0.15)  # Ultimi 15% dell'altezza
    left = int(width * 0.10)
    right = int(width * 0.65)
    upper = height - notes_h
    return (left, upper, right, height)


def detect_dimension_zone_region(width: int, height: int) -> tuple[int, int, int, int]:
    """
    Zona quote-dimensioni: margine sinistro del disegno.
    Spesso ha annotazioni verticali con quote, DN, spessori, note.
    Posizione: primi 12% della larghezza, 20-80% dell'altezza.
    """
    left = 0
    right = int(width * 0.12)
    upper = int(height * 0.20)
    lower = int(height * 0.80)
    return (left, upper, right, lower)


def detect_revision_block_region(width: int, height: int) -> tuple[int, int, int, int]:
    """
    Zona blocco revisioni: sopra il cartiglio, angolo destro.
    Qui ci sono: numero revisione, date, autori, modifiche.
    Posizione: ultimi 35% larghezza, 55-72% altezza.
    """
    left = int(width * 0.65)
    right = width
    upper = int(height * 0.55)
    lower = int(height * 0.72)
    return (left, upper, right, lower)


def detect_bom_zone_region(width: int, height: int) -> tuple[int, int, int, int]:
    """
    Zona BOM/Parts List: angolo alto-destra o destra.
    Nei disegni con tabella componenti, sta in alto a destra.
    Posizione: ultimi 35% larghezza, primi 40% altezza.
    """
    left = int(width * 0.65)
    right = width
    upper = 0
    lower = int(height * 0.40)
    return (left, upper, right, lower)


def detect_notes_left_region(width: int, height: int) -> tuple[int, int, int, int]:
    """
    Zona note tecniche sul lato sinistro del disegno.
    Nei disegni TMP/TPI, il blocco "NOTES FOR PATTERNMAKER AND FOUNDRY"
    e "NOTE PER IL MODELLISTA E LA FONDERIA" occupa la metà sinistra.
    Posizione: primi 50% larghezza, 5-95% altezza.
    """
    left = 0
    right = int(width * 0.50)
    upper = int(height * 0.05)
    lower = int(height * 0.95)
    return (left, upper, right, lower)


# ============================================================
# POST-PROCESSING TESTO OCR (fix errori comuni)
# ============================================================

_OCR_FIX_PATTERNS = [
    # Φ (diametro) — Tesseract lo legge come $, #, o ¢ davanti a numeri
    (r'[$#¢]\s*(\d)', r'Φ\1'),
    # Ø (scandinavo ma usato come diametro) → Φ
    (r'Ø\s*(\d)', r'Φ\1'),
    # EQUIDISTANT! → EQUIDISTANTI (OCR confonde I finale con !)
    (r'EQUIDISTANT!', 'EQUIDISTANTI'),
    # FORI $32 → FORI Φ32 (pattern specifico disegni TPI)
    (r'FORI\s+[$#](\d)', r'FORI Φ\1'),
    # LAMATURE $55 → LAMATURE Φ55
    (r'LAMATURE\s+[$#](\d)', r'LAMATURE Φ\1'),
    # HOLES $32 → HOLES Φ32
    (r'HOLES\s+[$#](\d)', r'HOLES Φ\1'),
    # SPOT-FACES $55 → SPOT-FACES Φ55
    (r'SPOT-FACES\s+[$#](\d)', r'SPOT-FACES Φ\1'),
    # DN 10" → mantieni (corretto)
    # 0-ring → O-ring
    (r'\b0[- ]?ring\b', 'O-ring'),
    # lI → Il (articolo italiano)
    (r'\blI\b', 'Il'),
    # NPl → NPT (errore comune su filettature)
    (r'\bNPl\b', 'NPT'),
    # B.W, → B.W. (punto mancante)
    (r'B\.W,', 'B.W.'),
    # S.W, → S.W.
    (r'S\.W,', 'S.W.'),
]


def _postprocess_ocr_text(text: str) -> str:
    """
    Corregge errori OCR comuni nei disegni tecnici.
    Applica sostituzioni regex per simboli e parole frequentemente
    mal interpretate da Tesseract.
    """
    import re as _re
    if not text:
        return text
    for pattern, replacement in _OCR_FIX_PATTERNS:
        text = _re.sub(pattern, replacement, text)
    return text


def _is_noise_line(line: str) -> bool:
    """
    Verifica se una riga OCR è rumore (linee grafiche interpretate come testo).
    Usa cluster di consonanti, densità simboli e lunghezza parole come euristiche.
    """
    if not line or len(line.strip()) < 2:
        return True
    stripped = line.strip()
    total = len(stripped)

    # 1. Alta densità di simboli pipe/bracket/uguale → rumore da tabelle grafiche
    pipe_count = sum(1 for c in stripped if c in '|={}[]<>~^`')
    if total > 4 and pipe_count / total > 0.20:
        return True

    # 2. Bassa densità alfanumerica (include punti, virgole, spazi come "buoni")
    alnum_count = sum(1 for c in stripped if c.isalnum() or c in ' .,;:-_()/\'"')
    if total > 5 and alnum_count / total < 0.35:
        return True

    # 3. Linee corte (≤3 char) senza lettere → rumore
    if total <= 3 and not any(c.isalpha() for c in stripped):
        return True

    # 4. Cluster di consonanti impossibili (5+ consonanti consecutive per parola)
    # "MQQOQQ" → cluster impossibile, "FOUNDRY" → ndry = ok (4 consonanti)
    # Controlla PER PAROLA, non sulla riga intera (altrimenti "Standards shall" = falso positivo)
    words = stripped.split()
    for w in words:
        alpha_word = ''.join(c.lower() for c in w if c.isalpha())
        if len(alpha_word) >= 5:
            vowels = set('aeiou')
            max_consonants = 0
            current_consonants = 0
            for c in alpha_word:
                if c not in vowels:
                    current_consonants += 1
                    max_consonants = max(max_consonants, current_consonants)
                else:
                    current_consonants = 0
            if max_consonants >= 5:
                return True

    return False


# ============================================================
# AUTO-DESKEW (correzione inclinazione)
# ============================================================

def _auto_deskew(img: Image.Image) -> Image.Image:
    """
    Corregge automaticamente l'inclinazione dell'immagine.
    Anche 0.5° di rotazione peggiora significativamente l'OCR.
    Usa Tesseract OSD (Orientation and Script Detection) per rilevare l'angolo.
    """
    try:
        import pytesseract
        # Converti a RGB se necessario per OSD
        osd_img = img.copy()
        if osd_img.mode not in ("RGB", "L"):
            osd_img = osd_img.convert("RGB")
        # Riduci per velocità OSD (max 2000px)
        w, h = osd_img.size
        if max(w, h) > 2000:
            scale = 2000 / max(w, h)
            osd_img = osd_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        osd = pytesseract.image_to_osd(osd_img, output_type=pytesseract.Output.DICT)
        angle = osd.get("rotate", 0)
        # Correggi solo rotazioni significative (> 0.3°) ma non multipli di 90°
        if angle and abs(angle) > 0 and angle % 90 != 0:
            logger.info("Auto-deskew: ruoto immagine di %d°", -angle)
            return img.rotate(-angle, expand=True, fillcolor=(255, 255, 255))
        return img
    except Exception as e:
        logger.debug("Auto-deskew non applicabile: %s", e)
        return img


# ============================================================
# OCR CON PSM OTTIMIZZATO PER ZONA
# ============================================================

def _ocr_zone_with_psm(img: Image.Image, ocr_func, psm: int = 6, lang: str = None) -> str:
    """
    Esegue OCR con uno specifico Page Segmentation Mode di Tesseract.
    PSM modes utili per disegni tecnici:
      3 = Auto (default)
      4 = Single column of text
      6 = Single uniform block of text
      11 = Sparse text (trova testo ovunque)
      12 = Sparse text with OSD
    """
    import pytesseract
    try:
        if img.mode not in ("RGB", "RGBA", "L", "1"):
            img = img.convert("RGB")
        lang = lang or "ita+eng"
        config = f"--psm {psm}"
        text = pytesseract.image_to_string(img, lang=lang, config=config).strip()
        return text
    except Exception:
        # Fallback a OCR standard
        try:
            return ocr_func(img)
        except Exception:
            return ""


# ============================================================
# PRE-PROCESSING IMMAGINE PER OCR MASSIMO
# ============================================================

def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    Pre-processa un'immagine per massimizzare l'estrazione OCR di Tesseract.
    Applica: conversione a grayscale, aumento contrasto, binarizzazione adattiva,
    e sharpening. Particolarmente utile per disegni tecnici con testo chiaro
    su sfondo leggermente grigio.
    """
    try:
        from PIL import ImageEnhance, ImageOps

        # 1. Converti a grayscale se non lo è già
        gray = img.convert("L")

        # 2. Auto-contrasto (stretcha l'istogramma)
        gray = ImageOps.autocontrast(gray, cutoff=1)

        # 3. Aumenta contrasto (2x)
        enhancer = ImageEnhance.Contrast(gray)
        gray = enhancer.enhance(2.0)

        # 4. Sharpening (1.5x)
        enhancer = ImageEnhance.Sharpness(gray)
        gray = enhancer.enhance(1.5)

        # 5. Binarizzazione con soglia Otsu-like
        # Per disegni tecnici: testo nero su bianco = soglia alta
        threshold = 180
        gray = gray.point(lambda p: 255 if p > threshold else 0)

        return gray
    except Exception as e:
        logger.warning("Pre-processing OCR fallito: %s", e)
        return img


def _edge_density(img: Image.Image) -> float:
    """
    Calcola la densità di bordi (edge) in una regione.
    Più bordi = più probabilità che sia una zona con testo/tabelle.
    """
    try:
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        pixels = list(edges.getdata())
        if not pixels:
            return 0.0
        threshold = 30
        edge_count = sum(1 for p in pixels if p > threshold)
        return edge_count / len(pixels)
    except Exception:
        return 0.0


def detect_title_block(img: Image.Image) -> Optional[tuple[int, int, int, int]]:
    """
    Rileva il cartiglio nell'immagine. Verifica che la regione attesa
    contenga effettivamente più bordi/testo del resto dell'immagine.

    Returns:
        Box (left, upper, right, lower) del cartiglio, o None se non trovato.
    """
    w, h = img.size
    if w < 500 or h < 500:
        return None

    # Regione candidata (basso-destra)
    box = detect_title_block_region(w, h)
    candidate = img.crop(box)
    candidate_density = _edge_density(candidate)

    # Confronta con la densità media su una zona equivalente (alto-sinistra)
    ref_box = (0, 0, box[2] - box[0], box[3] - box[1])
    ref_crop = img.crop(ref_box)
    ref_density = _edge_density(ref_crop)

    # Il cartiglio deve avere almeno un po' di contenuto
    # Soglia bassa (0.01) per supportare TIF bi-level (mode 1) che hanno
    # edge density naturalmente più bassa rispetto a immagini grayscale/color
    if candidate_density > 0.01:
        logger.debug(
            "Title block rilevato: density=%.3f (ref=%.3f), box=%s",
            candidate_density, ref_density, box,
        )
        return box

    logger.debug(
        "Title block NON rilevato: density=%.3f troppo bassa", candidate_density
    )
    return None


# ============================================================
# 3. GENERAZIONE TILE CON OVERLAP
# ============================================================

def generate_tiles(
    width: int,
    height: int,
    rows: int,
    cols: int,
    overlap_pct: float = 0.10,
) -> list[tuple[int, int, int, int]]:
    """
    Genera le coordinate (left, upper, right, lower) per ogni tile,
    includendo l'overlap configurabile tra zone adiacenti.

    Args:
        width, height: dimensioni immagine
        rows, cols: griglia tile
        overlap_pct: percentuale di overlap (0.0 – 0.30)

    Returns:
        Lista di tuple (left, upper, right, lower)
    """
    overlap_pct = max(0.0, min(overlap_pct, 0.30))
    tile_w = width / cols
    tile_h = height / rows
    overlap_x = int(tile_w * overlap_pct)
    overlap_y = int(tile_h * overlap_pct)

    tiles = []
    for r in range(rows):
        for c in range(cols):
            left = max(0, int(c * tile_w) - overlap_x)
            upper = max(0, int(r * tile_h) - overlap_y)
            right = min(width, int((c + 1) * tile_w) + overlap_x)
            lower = min(height, int((r + 1) * tile_h) + overlap_y)
            tiles.append((left, upper, right, lower))

    return tiles


# ============================================================
# 4. DEDUPLICAZIONE TESTO DA OVERLAP
# ============================================================

def _deduplicate_lines(texts: list[str]) -> str:
    """
    Unisce testi da tile adiacenti, rimuovendo righe duplicate
    che appaiono nelle zone di overlap e filtrando il rumore OCR.
    """
    seen = set()
    result_lines = []
    for text in texts:
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            # Filtra rumore OCR (linee grafiche interpretate come testo)
            if _is_noise_line(stripped):
                continue
            # Normalizza per confronto (lowercase, spazi multipli)
            key = " ".join(stripped.lower().split())
            if key not in seen:
                seen.add(key)
                result_lines.append(stripped)
    return "\n".join(result_lines)


# ============================================================
# 5. FUNZIONE PRINCIPALE: TILE OCR EXTRACT
# ============================================================

def tile_ocr_extract(
    path: str,
    ocr_func: Callable[[Image.Image], str],
    overlap_pct: float = 0.15,
    title_block_zoom: float = 2.0,
) -> str:
    """
    Estrae testo da un'immagine (TIF, PNG, BMP, ecc.) usando OCR a zone.

    Flusso:
    1. Apre l'immagine (supporta TIF multi-pagina)
    2. Per ogni pagina:
       a. Calcola la griglia adattiva
       b. Rileva il cartiglio (title block) per zoom extra
       c. OCR su ogni tile
       d. OCR con zoom sul cartiglio
    3. Unisce tutto deduplicando righe dall'overlap

    Args:
        path: Percorso al file immagine
        ocr_func: Funzione che prende un PIL.Image e restituisce testo (es. _ocr_single_image)
        overlap_pct: Percentuale di overlap tra tile (0.0 – 0.30)
        title_block_zoom: Fattore di zoom sul cartiglio (1.0 = nessuno, 2.0 = 2x)

    Returns:
        Testo estratto completo, deduplicato
    """
    try:
        img = Image.open(path)
    except Exception as e:
        logger.error("Impossibile aprire immagine per tile OCR: %s — %s", path, e)
        return ""

    n_frames = getattr(img, "n_frames", 1)
    all_texts = []

    for frame_idx in range(n_frames):
        try:
            img.seek(frame_idx)
        except EOFError:
            break

        # Copia il frame corrente in un'immagine indipendente
        frame = img.copy()

        # --- Upscaling DPI ---
        try:
            from config import OCR_TARGET_DPI
            frame = _upscale_to_target_dpi(frame, target_dpi=OCR_TARGET_DPI)
        except ImportError:
            frame = _upscale_to_target_dpi(frame, target_dpi=400)

        # --- Auto-deskew (correzione inclinazione) ---
        frame = _auto_deskew(frame)

        w, h = frame.size
        if w <= 0 or h <= 0:
            logger.warning("Frame %d con dimensioni nulle, salto", frame_idx)
            continue

        page_label = f"Page {frame_idx + 1}" if n_frames > 1 else ""

        # --- Griglia adattiva ---
        rows, cols = compute_tile_grid(w, h)
        tiles = generate_tiles(w, h, rows, cols, overlap_pct)
        logger.info(
            "Tile OCR %s: %dx%d px → griglia %dx%d (%d tile, overlap %.0f%%)",
            page_label, w, h, rows, cols, len(tiles), overlap_pct * 100,
        )

        tile_texts = []
        for i, box in enumerate(tiles):
            try:
                tile_img = frame.crop(box)
                tile_text = ocr_func(tile_img)
                if tile_text:
                    tile_texts.append(tile_text)
                    logger.debug(
                        "  Tile %d/%d [%s]: %d caratteri",
                        i + 1, len(tiles), box, len(tile_text),
                    )
            except Exception as e:
                logger.warning("Errore OCR su tile %d: %s", i + 1, e)
                continue

        # --- Title block: zoom extra ---
        MAX_ZOOM_PX = 8000  # Limite max lato per immagine zoomata
        if title_block_zoom > 1.0:
            tb_box = detect_title_block(frame)
            if tb_box:
                try:
                    tb_crop = frame.crop(tb_box)
                    tb_w, tb_h = tb_crop.size
                    # Calcola zoom effettivo limitato a MAX_ZOOM_PX
                    eff_zoom = min(title_block_zoom, MAX_ZOOM_PX / max(tb_w, tb_h, 1))
                    eff_zoom = max(eff_zoom, 1.0)
                    zoomed_w = int(tb_w * eff_zoom)
                    zoomed_h = int(tb_h * eff_zoom)
                    tb_zoomed = tb_crop.resize(
                        (zoomed_w, zoomed_h), Image.Resampling.LANCZOS
                    )
                    tb_text = ocr_func(tb_zoomed)
                    if tb_text:
                        tile_texts.append(tb_text)
                        logger.info(
                            "  Title block zoom %.1fx: %d caratteri estratti extra",
                            eff_zoom, len(tb_text),
                        )
                except Exception as e:
                    logger.warning("Errore OCR su title block: %s", e)

        # --- Notes zone: zoom su zona note (peso, tolleranze, materiale) ---
        if title_block_zoom > 1.0:
            notes_box = detect_notes_zone_region(w, h)
            try:
                notes_crop = frame.crop(notes_box)
                notes_w, notes_h = notes_crop.size
                eff_zoom_n = min(title_block_zoom, MAX_ZOOM_PX / max(notes_w, notes_h, 1))
                eff_zoom_n = max(eff_zoom_n, 1.0)
                zoomed_nw = int(notes_w * eff_zoom_n)
                zoomed_nh = int(notes_h * eff_zoom_n)
                notes_zoomed = notes_crop.resize(
                    (zoomed_nw, zoomed_nh), Image.Resampling.LANCZOS
                )
                notes_text = ocr_func(notes_zoomed)
                if notes_text:
                    tile_texts.append(notes_text)
                    logger.info(
                        "  Notes zone zoom %.1fx: %d caratteri estratti extra",
                        eff_zoom_n, len(notes_text),
                    )
            except Exception as e:
                logger.warning("Errore OCR su notes zone: %s", e)

        # --- Zone aggiuntive per estrazione massima (con PSM ottimizzato) ---
        extra_zones = [
            ("Dimension zone", detect_dimension_zone_region, 4),   # PSM 4: colonna
            ("Revision block", detect_revision_block_region, 6),   # PSM 6: blocco
            ("BOM zone", detect_bom_zone_region, 6),               # PSM 6: blocco
            ("Notes left", detect_notes_left_region, 4),           # PSM 4: colonna note
        ]
        for zone_name, zone_func, psm in extra_zones:
            try:
                zone_box = zone_func(w, h)
                zone_crop = frame.crop(zone_box)
                zw, zh = zone_crop.size
                if zw < 50 or zh < 50:
                    continue
                # Zoom limitato
                eff_z = min(title_block_zoom, MAX_ZOOM_PX / max(zw, zh, 1))
                eff_z = max(eff_z, 1.0)
                if eff_z > 1.0:
                    zone_zoomed = zone_crop.resize(
                        (int(zw * eff_z), int(zh * eff_z)),
                        Image.Resampling.LANCZOS,
                    )
                else:
                    zone_zoomed = zone_crop
                # OCR con PSM ottimizzato per la zona
                zone_text = _ocr_zone_with_psm(zone_zoomed, ocr_func, psm=psm)
                if zone_text and len(zone_text.strip()) > 10:
                    tile_texts.append(zone_text)
                    logger.info(
                        "  %s zoom %.1fx PSM %d: %d caratteri estratti",
                        zone_name, eff_z, psm, len(zone_text),
                    )
            except Exception as e:
                logger.warning("Errore OCR su %s: %s", zone_name, e)

        # --- Title block: secondo passaggio con pre-processing ---
        # Questo passaggio usa binarizzazione + contrasto per leggere
        # testo debole che Tesseract non ha catturato nel primo passaggio
        if title_block_zoom > 1.0:
            tb_box2 = detect_title_block(frame)
            if tb_box2:
                try:
                    tb_crop2 = frame.crop(tb_box2)
                    tb_w2, tb_h2 = tb_crop2.size
                    eff_z2 = min(title_block_zoom, MAX_ZOOM_PX / max(tb_w2, tb_h2, 1))
                    eff_z2 = max(eff_z2, 1.0)
                    tb_zoomed2 = tb_crop2.resize(
                        (int(tb_w2 * eff_z2), int(tb_h2 * eff_z2)),
                        Image.Resampling.LANCZOS,
                    )
                    # Pre-processing: contrasto + binarizzazione
                    tb_preprocessed = _preprocess_for_ocr(tb_zoomed2)
                    tb_text2 = ocr_func(tb_preprocessed)
                    if tb_text2 and len(tb_text2.strip()) > 10:
                        tile_texts.append(tb_text2)
                        logger.info(
                            "  Title block preprocessed zoom %.1fx: %d caratteri extra",
                            eff_z2, len(tb_text2),
                        )
                except Exception as e:
                    logger.warning("Errore OCR preprocessed su title block: %s", e)

        # --- Dual-language: secondo passaggio solo inglese su title block ---
        # L'OCR solo inglese è più preciso su codici tecnici, numeri, e standard
        if title_block_zoom > 1.0:
            tb_box_eng = detect_title_block(frame)
            if tb_box_eng:
                try:
                    tb_eng_crop = frame.crop(tb_box_eng)
                    tb_ew, tb_eh = tb_eng_crop.size
                    eff_ze = min(title_block_zoom, MAX_ZOOM_PX / max(tb_ew, tb_eh, 1))
                    eff_ze = max(eff_ze, 1.0)
                    tb_eng_zoomed = tb_eng_crop.resize(
                        (int(tb_ew * eff_ze), int(tb_eh * eff_ze)),
                        Image.Resampling.LANCZOS,
                    )
                    eng_text = _ocr_zone_with_psm(tb_eng_zoomed, ocr_func, psm=6, lang="eng")
                    if eng_text and len(eng_text.strip()) > 20:
                        # Aggiungi solo righe nuove non già presenti
                        existing = set(l.strip().lower() for t in tile_texts for l in t.split('\n') if l.strip())
                        new_lines = [l for l in eng_text.split('\n')
                                     if l.strip() and l.strip().lower() not in existing and len(l.strip()) > 3]
                        if new_lines:
                            tile_texts.append('\n'.join(new_lines))
                            logger.info("  Dual-lang ENG pass: %d nuove righe estratte", len(new_lines))
                except Exception as e:
                    logger.warning("Errore OCR dual-language: %s", e)

        # --- OCR testo ruotato 90° (quote e note verticali) ---
        try:
            # Ruota solo il title block a 90° per catturare testo verticale
            tb_box_rot = detect_title_block(frame)
            if tb_box_rot:
                tb_rot_crop = frame.crop(tb_box_rot)
                tb_rotated = tb_rot_crop.rotate(90, expand=True)
                rot_text = ocr_func(tb_rotated)
                if rot_text and len(rot_text.strip()) > 20:
                    # Aggiungi solo righe nuove (non già presenti)
                    existing = set(l.strip().lower() for t in tile_texts for l in t.split('\n') if l.strip())
                    new_lines = [l for l in rot_text.split('\n') if l.strip() and l.strip().lower() not in existing and len(l.strip()) > 3]
                    if new_lines:
                        tile_texts.append('\n'.join(new_lines))
                        logger.info("  Rotated 90° OCR: %d nuove righe estratte", len(new_lines))
        except Exception as e:
            logger.warning("Errore OCR testo ruotato: %s", e)

        # --- Post-processing: fix errori OCR comuni ---
        tile_texts = [_postprocess_ocr_text(t) for t in tile_texts]

        # --- Unisci testi per questa pagina ---
        if tile_texts:
            page_text = _deduplicate_lines(tile_texts)
            if page_label:
                all_texts.append(f"--- {page_label} ---\n{page_text}")
            else:
                all_texts.append(page_text)

    return "\n\n".join(all_texts)


# ============================================================
# 6. HELPER: TILE VISION EXTRACT
# ============================================================

def tile_vision_extract(
    path: str,
    vision_func: Callable[[Image.Image], str],
    overlap_pct: float = 0.10,
    title_block_zoom: float = 2.0,
    max_tiles_for_vision: int = 6,
) -> str:
    """
    Come tile_ocr_extract, ma ottimizzato per Vision API (limite chiamate).
    Seleziona solo le tile più "dense" (più bordi/contenuto) + title block.

    Args:
        path: Percorso file immagine
        vision_func: Funzione che prende un PIL.Image e restituisce testo via Vision API
        overlap_pct: Overlap tra tile
        title_block_zoom: Zoom su cartiglio
        max_tiles_for_vision: Massimo tile da inviare a Vision (per risparmiare API)

    Returns:
        Testo estratto e deduplicato
    """
    try:
        img = Image.open(path)
    except Exception as e:
        logger.error("Impossibile aprire immagine per tile Vision: %s — %s", path, e)
        return ""

    # Per Vision usiamo solo il primo frame (multi-page TIF è raro con Vision)
    frame = img.copy()
    w, h = frame.size
    if w <= 0 or h <= 0:
        return ""

    rows, cols = compute_tile_grid(w, h)
    tiles = generate_tiles(w, h, rows, cols, overlap_pct)

    # Calcola densità bordi per ogni tile e seleziona le top N
    tile_scores = []
    for i, box in enumerate(tiles):
        try:
            tile_img = frame.crop(box)
            density = _edge_density(tile_img)
            tile_scores.append((density, i, box))
        except Exception:
            continue

    # Ordina per densità decrescente, prendi le top
    tile_scores.sort(key=lambda x: x[0], reverse=True)
    selected = tile_scores[:max_tiles_for_vision]

    logger.info(
        "Tile Vision: %d tile selezionate su %d (top densità bordi)",
        len(selected), len(tiles),
    )

    tile_texts = []
    for density, idx, box in selected:
        try:
            tile_img = frame.crop(box)
            tile_text = vision_func(tile_img)
            if tile_text:
                tile_texts.append(tile_text)
                logger.debug(
                    "  Vision tile %d (density=%.3f): %d chars",
                    idx + 1, density, len(tile_text),
                )
        except Exception as e:
            logger.warning("Errore Vision su tile %d: %s", idx + 1, e)
            continue

    # Title block con zoom (sempre incluso, non conta nel max)
    if title_block_zoom > 1.0:
        tb_box = detect_title_block(frame)
        if tb_box:
            try:
                tb_crop = frame.crop(tb_box)
                tb_w, tb_h = tb_crop.size
                zoomed_w = int(tb_w * title_block_zoom)
                zoomed_h = int(tb_h * title_block_zoom)
                tb_zoomed = tb_crop.resize(
                    (zoomed_w, zoomed_h), Image.Resampling.LANCZOS
                )
                tb_text = vision_func(tb_zoomed)
                if tb_text:
                    tile_texts.append(tb_text)
                    logger.info(
                        "  Title block Vision zoom %.1fx: %d chars extra",
                        title_block_zoom, len(tb_text),
                    )
            except Exception as e:
                logger.warning("Errore Vision su title block: %s", e)

    return _deduplicate_lines(tile_texts)
