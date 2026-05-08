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


def generate_pdf(csv_path: str, output_path: str, max_positions: int = None,
                 theme_filter: list[str] = None, difficulty_filter: list[str] = None,
                 group_by_difficulty: bool = False):
    """Generate PDF with chess positions from CSV file.

    Args:
        csv_path: Path to the CSV file
        output_path: Path for the output PDF
        max_positions: Limit to first N positions (for preview)
        theme_filter: List of themes to include (None = all themes)
        difficulty_filter: List of difficulty levels as strings ['1','2','3','4'] (None = all)
        group_by_difficulty: If True, create separate chapters per difficulty level
    """
    positions = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Apply difficulty filter
            if difficulty_filter and row['difficulty'] not in difficulty_filter:
                continue

            # Apply theme filter
            row_themes = get_themes(row)
            if theme_filter:
                # Include position if it has any of the filtered themes
                if not any(t in theme_filter for t in row_themes):
                    continue

            positions.append({
                'fen': row['fen'],
                'best_move': row['best_move'],
                'side_to_move': row['side_to_move'],
                'difficulty': int(row['difficulty']),
                'themes': row_themes,
            })

    if max_positions:
        positions = positions[:max_positions]
        print(f"Using first {max_positions} positions (for preview)")
    else:
        print(f"Loaded {len(positions)} positions")

    # Group by difficulty if requested
    if group_by_difficulty:
        grouped = {1: [], 2: [], 3: [], 4: []}
        for pos in positions:
            grouped[pos['difficulty']].append(pos)
        positions = grouped

def draw_chapter_title(c, title: str, subtitle: str = None):
    """Draw a chapter title page."""
    page_width, page_height = A4
    margin_top = 2.5 * cm

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(page_width / 2, page_height - margin_top, title)

    if subtitle:
        c.setFont("Helvetica", 14)
        c.drawCentredString(page_width / 2, page_height - margin_top - 1.2 * cm, subtitle)


def generate_pdf(csv_path: str, output_path: str, max_positions: int = None,
                 theme_filter: list[str] = None, difficulty_filter: list[str] = None,
                 group_by_difficulty: bool = False):
    """Generate PDF with chess positions from CSV file.

    Args:
        csv_path: Path to the CSV file
        output_path: Path for the output PDF
        max_positions: Limit to first N positions (for preview)
        theme_filter: List of themes to include (None = all themes)
        difficulty_filter: List of difficulty levels as strings ['1','2','3','4'] (None = all)
        group_by_difficulty: If True, create separate chapters per difficulty level
    """
    positions = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Apply difficulty filter
            if difficulty_filter and row['difficulty'] not in difficulty_filter:
                continue

            # Apply theme filter
            row_themes = get_themes(row)
            if theme_filter:
                # Include position if it has any of the filtered themes
                if not any(t in theme_filter for t in row_themes):
                    continue

            positions.append({
                'fen': row['fen'],
                'best_move': row['best_move'],
                'side_to_move': row['side_to_move'],
                'difficulty': int(row['difficulty']),
                'themes': row_themes,
            })

    if max_positions:
        positions = positions[:max_positions]
        print(f"Using first {max_positions} positions (for preview)")
    else:
        print(f"Loaded {len(positions)} positions")

    # Group by difficulty if requested
    if group_by_difficulty:
        grouped = {1: [], 2: [], 3: [], 4: []}
        for pos in positions:
            grouped[pos['difficulty']].append(pos)
        positions = grouped

    # Set PDF metadata (title that shows in PDF viewers)
    diff_labels_meta = {'1': 'Easy', '2': 'Moderate', '3': 'Hard', '4': 'Very Hard'}
    theme_display = THEME_DISPLAY_NAMES

    title_parts = ["Chess Positions"]
    if theme_filter:
        display_themes = [theme_display.get(t, t).replace(' ', '') for t in theme_filter]
        title_parts.append('-'.join(display_themes))
    if difficulty_filter:
        display_diffs = [diff_labels_meta[d] for d in difficulty_filter]
        title_parts.append('-'.join(display_diffs))

    pdf_title = ' '.join(title_parts)[:50]  # PDF title limit

    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle(pdf_title)
    c.setAuthor("Chess Position Analysis")
    c.setSubject("Positional Chess Puzzles")

    # Title page
    c.setFont("Helvetica-Bold", 24)
    title_y = 7 * cm
    c.drawCentredString(A4[0] / 2, A4[1] / 2 + title_y, "Chess Position Analysis")

    subtitle_parts = []
    if theme_filter:
        display_themes = [theme_display.get(t, t) for t in theme_filter]
        subtitle_parts.append(f"Themes: {', '.join(display_themes)}")
    if difficulty_filter:
        subtitle_parts.append(f"Difficulty: {', '.join(diff_labels_meta[d] for d in difficulty_filter)}")
    if group_by_difficulty:
        subtitle_parts.append("(grouped by difficulty)")

    if subtitle_parts:
        c.setFont("Helvetica", 12)
        c.drawCentredString(A4[0] / 2, A4[1] / 2 + title_y - 1.2 * cm, " | ".join(subtitle_parts))

    c.showPage()

    # Credits/Attribution page
    margin_left = 2 * cm
    margin_top = 2 * cm
    page_width, page_height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_left, page_height - margin_top, "Credits & Attribution")

    c.setFont("Helvetica", 11)
    y = page_height - margin_top - 1.2 * cm

    lines = [
        "These positional chess puzzles were curated from the Lichess games database",
        "and reviewed by titled players.",
        "",
        "Main Contributor:",
        "  Neil G.D. (neilgd) - Repository creator and data miner",
        "",
        "Titled Player Reviewers:",
        "  WIM/FM Liwia Jarocka",
        "  WGM Michalina Rudzinska",
        "  WGM Margarita Voyska",
        "",
        "Additional Contributions:",
        "  Vlad Ghita - Machine learning exploration",
        "  Fiddler - Guidance on position selection",
        "",
        "Repository:",
        "  https://github.com/neilgd/chess-position-analysis-results",
        "",
        "License: Free to use with attribution. Please link back to the repository",
        "when using this dataset.",
    ]

    for line in lines:
        c.drawString(margin_left, y, line)
        y -= 0.5 * cm

    c.showPage()

    # --- Position diagrams ---
    positions_per_page = 12
    cols = 3
    rows = 4

    global_position_num = 0

    def render_positions(pos_list, start_num=True):
        nonlocal global_position_num
        if start_num:
            global_position_num = 0

        for i, pos in enumerate(pos_list):
            page_num = i // positions_per_page
            pos_on_page = i % positions_per_page

            if pos_on_page == 0 and page_num > 0:
                c.showPage()

            col = pos_on_page % cols
            row = pos_on_page // cols

            global_position_num += 1
            pos['global_num'] = global_position_num

            draw_position_on_pdf(
                c,
                pos['fen'],
                pos['side_to_move'],
                pos['difficulty'],
                pos['themes'],
                global_position_num,
                col,
                row
            )

    # Track position numbers across chapters
    if group_by_difficulty:
        diff_labels = {
            1: ("Chapter 1", "Easy Positions (1200–1500)"),
            2: ("Chapter 2", "Moderate Positions (1500–1800)"),
            3: ("Chapter 3", "Hard Positions (1800–2000)"),
            4: ("Chapter 4", "Very Hard Positions (2000+)"),
        }

        first_chapter = True
        for diff in [1, 2, 3, 4]:
            chapter_positions = positions.get(diff, [])
            if not chapter_positions:
                continue

            # Chapter title page (not for first chapter - title page serves as intro)
            if not first_chapter:
                draw_chapter_title(c, diff_labels[diff][0], diff_labels[diff][1])
                c.showPage()
            first_chapter = False

            # Render positions for this chapter
            render_positions(chapter_positions, start_num=False)

            # Finalize the page after rendering, so next chapter title doesn't overlap
            c.showPage()
    else:
        render_positions(positions, start_num=True)

    # --- Solutions section ---
    # Rebuild flat list with global numbers
    solutions_positions = []
    if group_by_difficulty:
        for diff in [1, 2, 3, 4]:
            solutions_positions.extend(positions.get(diff, []))
    else:
        solutions_positions = positions

    for pos in solutions_positions:
        pos['num'] = pos.get('global_num', len(solutions_positions))

    solutions_cols = 5
    solutions_per_page = 325  # 5 cols × 65 rows

    for chunk_start in range(0, len(solutions_positions), solutions_per_page):
        chunk = solutions_positions[chunk_start:chunk_start + solutions_per_page]
        c.showPage()
        draw_solutions_page(c, chunk, solutions_per_page, solutions_cols)

    c.save()
    print(f"PDF saved to {output_path}")


THEME_CHOICES = [
    "initiative", "development", "endgame", "space", "trading",
    "prophylaxis", "coordination", "exploitingweakness", "kingsafety",
    "restriction", "fixingstructure", "centrecontrol", "other"
]

THEME_DISPLAY_NAMES = {
    "initiative": "Initiative",
    "development": "Development",
    "endgame": "Endgame",
    "space": "Space",
    "trading": "Trading",
    "prophylaxis": "Prophylaxis",
    "coordination": "Coordination",
    "exploitingweakness": "Exploiting Weakness",
    "kingsafety": "King Safety",
    "restriction": "Restriction",
    "fixingstructure": "Fixing Structure",
    "centrecontrol": "Centre Control",
    "other": "Other",
}


def list_themes():
    """Print available themes with their display names."""
    print("Available themes:")
    for key in THEME_CHOICES:
        display = THEME_DISPLAY_NAMES.get(key, key)
        print(f"  {key:20s} — {display}")


if __name__ == "__main__":
    import os
    import sys
    import argparse

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "chess-positions.csv")

    parser = argparse.ArgumentParser(
        description="Generate PDF with chess position diagrams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Themes: Use --list-themes to see all available themes.
Example: python3 generate-pdf.py --theme endgame --theme prophylaxis --difficulty 1 --difficulty 2 --group-by-difficulty
"""
    )
    parser.add_argument("--output", "-o", default=None, help="Output PDF path")
    parser.add_argument("--theme", "-t", action="append", dest="themes",
                        choices=THEME_CHOICES,
                        help="Filter by theme (can be specified multiple times)")
    parser.add_argument("--difficulty", "-d", action="append", dest="difficulties",
                        choices=["1", "2", "3", "4"],
                        help="Filter by difficulty level 1-4 (can be specified multiple times)")
    parser.add_argument("--group-by-difficulty", "-g", action="store_true",
                        help="Group positions into chapters by difficulty level")
    parser.add_argument("--preview", "-p", action="store_true",
                        help="Generate preview with first 24 positions")
    parser.add_argument("--list-themes", action="store_true",
                        help="List all available themes and exit")

    args = parser.parse_args()

    if args.list_themes:
        list_themes()
        sys.exit(0)

    output_path = args.output or os.path.join(base_dir, "data", "chess-positions-diagrams.pdf")
    max_positions = 24 if args.preview else None

    # Build theme filter from single/theme selection
    theme_filter = args.themes if args.themes else None
    difficulty_filter = args.difficulties if args.difficulties else None

    generate_pdf(
        csv_path,
        output_path,
        max_positions=max_positions,
        theme_filter=theme_filter,
        difficulty_filter=difficulty_filter,
        group_by_difficulty=args.group_by_difficulty
    )