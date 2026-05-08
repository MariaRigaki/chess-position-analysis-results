# PDF Generation Script

Generate PDFs with chess position diagrams from the dataset.

## Usage

```bash
python3 generate-pdf.py [options]
```

## Options

| Option | Description |
|--------|-------------|
| `--output PATH, -o PATH` | Output PDF path (default: `data/chess-positions-diagrams.pdf`) |
| `--theme THEME, -t THEME` | Filter by theme (can be specified multiple times) |
| `--difficulty N, -d N` | Filter by difficulty level 1-4 (can be specified multiple times) |
| `--group-by-difficulty, -g` | Group positions into chapters by difficulty level |
| `--preview, -p` | Generate preview with first 24 positions |
| `--list-themes` | List all available themes and exit |
| `--help, -h` | Show help message |

## Examples

### Generate full PDF with all positions
```bash
python3 generate-pdf.py
```

### Generate PDF grouped by difficulty (creates chapter pages)
```bash
python3 generate-pdf.py --group-by-difficulty -o data/full-collection.pdf
```

### Filter by theme(s)
```bash
# Single theme
python3 generate-pdf.py --theme endgame -o data/endgame-puzzles.pdf

# Multiple themes (positions matching any of the themes)
python3 generate-pdf.py --theme coordination --theme restriction -o data/coord-restriction.pdf
```

### Filter by difficulty
```bash
# Easy and moderate only
python3 generate-pdf.py --difficulty 1 --difficulty 2 -o data/easy-moderate.pdf

# Hard and very hard
python3 generate-pdf.py --difficulty 3 --difficulty 4 -o data/hard-positions.pdf
```

### Combine filters with chapter grouping
```bash
python3 generate-pdf.py --theme endgame --difficulty 2 --difficulty 3 --group-by-difficulty -o data/endgame-mid-level.pdf
```

### Generate a quick preview
```bash
python3 generate-pdf.py --preview -o data/preview.pdf
```

### List all available themes
```bash
python3 generate-pdf.py --list-themes
```

## Available Themes

Run `--list-themes` to see all options. The 12 themes are:

- initiative
- development
- endgame
- space
- trading
- prophylaxis
- coordination
- exploitingweakness
- kingsafety
- restriction
- fixingstructure
- centrecontrol
- other

## PDF Structure

Each generated PDF contains:

1. **Title page** - Shows the title and applied filters
2. **Credits & Attribution page** - Acknowledges contributors and repository
3. **Position diagrams** - Chess positions (12 per page in 3×4 grid)
   - If `--group-by-difficulty`: Chapter title pages separate each difficulty level
4. **Solutions section** - Best moves listed at the end

## Requirements

```bash
pip install reportlab pillow chess cairosvg
```
