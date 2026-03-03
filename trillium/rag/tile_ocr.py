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
    che appaiono nelle zone di overlap.
    """
    seen = set()
    result_lines = []
    for text in texts:
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
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
    overlap_pct: float = 0.10,
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
        if title_block_zoom > 1.0:
            tb_box = detect_title_block(frame)
            if tb_box:
                try:
                    tb_crop = frame.crop(tb_box)
                    # Zoom: ridimensiona per avere effetto lente d'ingrandimento
                    tb_w, tb_h = tb_crop.size
                    zoomed_w = int(tb_w * title_block_zoom)
                    zoomed_h = int(tb_h * title_block_zoom)
                    tb_zoomed = tb_crop.resize(
                        (zoomed_w, zoomed_h), Image.Resampling.LANCZOS
                    )
                    tb_text = ocr_func(tb_zoomed)
                    if tb_text:
                        tile_texts.append(tb_text)
                        logger.info(
                            "  Title block zoom %.1fx: %d caratteri estratti extra",
                            title_block_zoom, len(tb_text),
                        )
                except Exception as e:
                    logger.warning("Errore OCR su title block: %s", e)

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
