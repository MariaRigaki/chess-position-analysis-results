#!/usr/bin/env python3
"""Generate a PDF with chess position diagrams from CSV data."""

import csv
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from PIL import Image
import chess
import chess.svg
import cairosvg

THEME_COLUMNS = [
    'initiative', 'development', 'endgame', 'space', 'trading',
    'prophylaxis', 'coordination', 'exploitingweakness', 'kingsafety',
    'restriction', 'fixingstructure', 'centrecontrol', 'other'
]

THEME_DISPLAY = {
    'initiative': 'initiative',
    'development': 'development',
    'endgame': 'endgame',
    'space': 'space',
    'trading': 'trading',
    'prophylaxis': 'prophylaxis',
    'coordination': 'coordination',
    'exploitingweakness': 'exploiting weakness',
    'kingsafety': 'king safety',
    'restriction': 'restriction',
    'fixingstructure': 'fixing structure',
    'centrecontrol': 'centre control',
    'other': 'other',
}


def get_stars(difficulty: int) -> str:
    return "★" * difficulty


def get_themes(row: dict) -> list[str]:
    themes = []
    for col in THEME_COLUMNS:
        if row.get(col, '0') == '1':
            themes.append(THEME_DISPLAY[col])
    return themes


def draw_position_on_pdf(c, fen: str, side_to_move: str, difficulty: int,
                         themes: list[str], position_num: int, col: int, row: int):
    """Draw a single chess position on the PDF canvas."""
    board = chess.Board(fen)

    page_width, page_height = A4
    margin_left = 1.7 * cm
    margin_right = 1.7 * cm
    margin_top = 1.2 * cm

    usable_width = page_width - margin_left - margin_right
    usable_height = page_height - margin_top - 0.8 * cm

    board_width = usable_width / 3
    board_height = usable_height / 4

    board_size = min(board_width, board_height) - 0.6 * cm

    x = margin_left + col * board_width + (board_width - board_size) / 2
    y = page_height - margin_top - (row + 1) * board_height + 1.0 * cm

    # Generate SVG board - grayscale, no coordinates, white at bottom
    svg = chess.svg.board(
        board,
        size=int(board_size * 10),
        coordinates=False,
        borders=True,
        flipped=False,
        colors={
            'square light': '#f0f0f0',
            'square dark': '#c8c8c8',
            'inner border': '#000000',
            'outer border': '#000000',
        }
    )

    try:
        png_bytes = cairosvg.svg2png(
            bytestring=svg.encode('utf-8'),
            output_width=int(board_size * 10),
            output_height=int(board_size * 10)
        )
        img = Image.open(BytesIO(png_bytes))
        img_reader = ImageReader(img)
        c.drawImage(img_reader, x, y, width=board_size, height=board_size)
    except Exception as e:
        print(f"Warning: Could not render board for position {position_num}: {e}")

    # Black dot outside bottom-right corner of the board if black to play
    if side_to_move == 'b':
        dot_x = x + board_size + 0.22 * cm
        dot_y = y + 0.15 * cm
        c.setFillColorRGB(0, 0, 0)
        c.circle(dot_x, dot_y, 2.5, fill=1)

    # Header above the board: position number, difficulty stars, themes
    header_y = y + board_size + 0.15 * cm
    header_x = x

    # Position number
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(header_x, header_y, f"{position_num}")

    # Difficulty stars
    stars = get_stars(difficulty)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.setFont("Helvetica", 7)
    star_x = header_x + 1.2 * cm
    c.drawString(star_x, header_y, stars)

    # Themes
    theme_str = ", ".join(themes) if themes else "general"
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 6)
    theme_x = star_x + 1.0 * cm
    c.drawString(theme_x, header_y, theme_str)


def uci_to_san(fen: str, uci_move: str) -> str:
    """Convert a UCI move to SAN notation given a FEN position."""
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci_move)
    return board.san(move)


def draw_solutions_page(c, positions: list[dict], solutions_per_page: int, cols: int):
    """Draw a solutions page with compact multi-column layout (vertical ordering)."""
    page_width, page_height = A4
    margin_left = 1.5 * cm
    margin_right = 1.5 * cm
    margin_top = 1.5 * cm

    usable_width = page_width - margin_left - margin_right
    col_width = usable_width / cols
    rows_per_col = (len(positions) + cols - 1) // cols

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_left, page_height - margin_top + 0.5 * cm, "Solutions")

    c.setFont("Helvetica", 8)

    for i, pos in enumerate(positions):
        col = i // rows_per_col
        row = i % rows_per_col

        x = margin_left + col * col_width
        y = page_height - margin_top - 0.8 * cm - row * (0.38 * cm)

        try:
            san = uci_to_san(pos['fen'], pos['best_move'])
        except Exception:
            san = pos['best_move']

        if pos['side_to_move'] == 'b':
            text = f"{pos['num']}  ... {san}"
        else:
            text = f"{pos['num']}  {san}"

        c.drawString(x, y, text)


def generate_pdf(csv_path: str, output_path: str, max_positions: int = None):
    """Generate PDF with chess positions from CSV file."""
    positions = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            positions.append({
                'fen': row['fen'],
                'best_move': row['best_move'],
                'side_to_move': row['side_to_move'],
                'difficulty': int(row['difficulty']),
                'themes': get_themes(row),
            })

    if max_positions:
        positions = positions[:max_positions]
        print(f"Using first {max_positions} positions (for preview)")
    else:
        print(f"Loaded {len(positions)} positions")

    c = canvas.Canvas(output_path, pagesize=A4)

    # --- Position diagrams ---
    positions_per_page = 12
    cols = 3
    rows = 4

    for i, pos in enumerate(positions):
        page_num = i // positions_per_page
        pos_on_page = i % positions_per_page

        if pos_on_page == 0 and page_num > 0:
            c.showPage()

        col = pos_on_page % cols
        row = pos_on_page // cols

        draw_position_on_pdf(
            c,
            pos['fen'],
            pos['side_to_move'],
            pos['difficulty'],
            pos['themes'],
            i + 1,
            col,
            row
        )

    # --- Solutions section ---
    for i, pos in enumerate(positions):
        pos['num'] = i + 1

    solutions_cols = 5
    solutions_per_page = 325  # 5 cols × 65 rows

    for chunk_start in range(0, len(positions), solutions_per_page):
        chunk = positions[chunk_start:chunk_start + solutions_per_page]
        c.showPage()
        draw_solutions_page(c, chunk, solutions_per_page, solutions_cols)

    c.save()
    print(f"PDF saved to {output_path}")


if __name__ == "__main__":
    import os
    import sys

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "chess-positions.csv")
    output_path = os.path.join(base_dir, "data", "chess-positions-diagrams.pdf")

    max_positions = None
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        max_positions = 24

    generate_pdf(csv_path, output_path, max_positions)