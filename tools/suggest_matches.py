"""Suggest Papirus candidates for unmapped xsi names (for manual review).

For each name in mapping/unmapped.txt, prints the closest Papirus symbolic
icon names by string similarity, plus any names sharing significant word
overlap. Output is a review aid only -- approved matches go into
mapping/overrides.tsv by hand.
"""

import difflib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAPIRUS = REPO / "vendor" / "papirus-icon-theme" / "Papirus"
UNMAPPED_TXT = REPO / "mapping" / "unmapped.txt"

SIZES = ("16x16", "22x22", "24x24")


def stem(name: str) -> str:
    return (
        name.removeprefix("xsi-")
        .removesuffix(".svg")
        .removesuffix("-rtl")
        .removesuffix("-symbolic")
    )


def main() -> None:
    inventory: set[str] = set()
    for size in SIZES:
        symbolic = PAPIRUS / size / "symbolic"
        if not symbolic.is_dir() or symbolic.is_symlink():
            continue
        for context_dir in symbolic.iterdir():
            if context_dir.is_dir():
                inventory.update(p.name for p in context_dir.glob("*.svg"))

    stems = {stem(n): n for n in sorted(inventory)}

    for xsi_name in UNMAPPED_TXT.read_text().split():
        target = stem(xsi_name)
        words = set(target.split("-"))

        close = difflib.get_close_matches(target, stems, n=3, cutoff=0.65)
        overlap = [
            s
            for s in stems
            if s not in close
            and len(words & set(s.split("-"))) >= max(1, len(words) - 1)
            and len(words | set(s.split("-"))) - len(words & set(s.split("-"))) <= 2
        ][:3]

        candidates = [stems[s] for s in close + overlap]
        print(f"{xsi_name}")
        for c in candidates:
            print(f"    ? {c}")
        if not candidates:
            print("    (no candidates)")


if __name__ == "__main__":
    main()
