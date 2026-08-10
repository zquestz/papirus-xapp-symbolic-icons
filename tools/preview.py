"""Render preview.png: a grid of every generated icon.

Renders the 16x16 variant of each icon at 2x (32 px) with rsvg-convert and
composites them into a single grid image on a light background (symbolic
icons are dark gray and would vanish on GitHub's dark mode without it).
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
ICONS_16 = REPO / "icons" / "Papirus" / "16x16" / "symbolic"
OUT = REPO / "preview.png"

ICON = 32  # rendered icon size (2x of 16 for crispness)
CELL = 44  # grid cell size
COLUMNS = 25
MARGIN = 16
BACKGROUND = (245, 245, 245, 255)


def main() -> None:
    svgs = sorted(ICONS_16.glob("*/*.svg"), key=lambda p: p.name)
    if not svgs:
        sys.exit("error: no generated icons found (run generate.py first)")

    rows = -(-len(svgs) // COLUMNS)
    image = Image.new(
        "RGBA",
        (2 * MARGIN + COLUMNS * CELL, 2 * MARGIN + rows * CELL),
        BACKGROUND,
    )

    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        for i, svg in enumerate(svgs):
            subprocess.run(
                [
                    "rsvg-convert",
                    "-w",
                    str(ICON),
                    "-h",
                    str(ICON),
                    "-o",
                    tmp.name,
                    str(svg),
                ],
                check=True,
            )
            icon = Image.open(tmp.name).convert("RGBA")
            x = MARGIN + (i % COLUMNS) * CELL + (CELL - ICON) // 2
            y = MARGIN + (i // COLUMNS) * CELL + (CELL - ICON) // 2
            image.alpha_composite(icon, (x, y))

    image.save(OUT)
    print(f"rendered {len(svgs)} icons -> {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
