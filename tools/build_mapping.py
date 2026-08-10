"""Build the xsi -> Papirus mapping table (exact matches only).

For every icon name shipped by upstream xapp-symbolic-icons, look for an
exact-name equivalent in the Papirus symbolic icon set:

  xsi-<name>-symbolic.svg      -> <name>-symbolic.svg
  xsi-<name>-symbolic-rtl.svg  -> <name>-symbolic-rtl.svg   (exact rtl)
                               or <name>-symbolic.svg        (mirrored)

Additionally, upstream ships many byte-identical icons under multiple names
(alias groups). Any name whose artwork is identical to an exactly-matched
name inherits that mapping: upstream declared the names equivalent, so no
judgment call is involved.

No fuzzy or concept matching is performed. Unmapped names are written to
mapping/unmapped.txt for a later pass.

Output: mapping/mapping.tsv with columns:
  xsi_name   papirus_name   method   contexts(size:context,...)

where method is one of copy | rtl-flip | alias-copy | alias-rtl-flip.
"""

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
XSI_DIR = REPO / "vendor" / "xapp-symbolic-icons" / "icons" / "symbolic"
PAPIRUS = REPO / "vendor" / "papirus-icon-theme" / "Papirus"

# Real (non-symlink) symbolic directories in the Papirus theme. Other sizes
# (32x32, symbolic-up-to-20, @2x) are symlinks to these and need no output.
SIZES = ("16x16", "22x22", "24x24")

MAPPING_TSV = REPO / "mapping" / "mapping.tsv"
UNMAPPED_TXT = REPO / "mapping" / "unmapped.txt"


def papirus_inventory() -> dict[str, list[tuple[str, str]]]:
    """Map icon filename -> [(size, context), ...] across real symbolic dirs."""
    inventory: dict[str, list[tuple[str, str]]] = {}
    for size in SIZES:
        symbolic = PAPIRUS / size / "symbolic"
        if not symbolic.is_dir() or symbolic.is_symlink():
            continue
        for context_dir in sorted(symbolic.iterdir()):
            if not context_dir.is_dir() or context_dir.is_symlink():
                continue
            for svg in sorted(context_dir.glob("*.svg")):
                inventory.setdefault(svg.name, []).append(
                    (size, context_dir.name)
                )
    return inventory


def xsi_names() -> list[str]:
    if not XSI_DIR.is_dir():
        sys.exit(f"error: {XSI_DIR} not found (init submodules first)")
    return sorted(p.name for p in XSI_DIR.glob("*.svg"))


def content_groups() -> dict[str, list[str]]:
    """Group upstream icon names by artwork content hash (symlinks resolved)."""
    groups: dict[str, list[str]] = {}
    for svg in sorted(XSI_DIR.glob("*.svg")):
        digest = hashlib.sha256(svg.read_bytes()).hexdigest()
        groups.setdefault(digest, []).append(svg.name)
    return groups


def main() -> None:
    inventory = papirus_inventory()
    names = xsi_names()

    mapped: dict[str, tuple[str, str]] = {}  # xsi_name -> (source, method)
    unmapped: list[str] = []

    # Stage 1: exact name matches (with rtl fallback to mirroring).
    for xsi_name in names:
        assert xsi_name.startswith("xsi-"), xsi_name
        base = xsi_name[len("xsi-"):]

        if base in inventory:
            mapped[xsi_name] = (base, "copy")
        elif base.endswith("-symbolic-rtl.svg"):
            ltr = base.removesuffix("-rtl.svg") + ".svg"
            if ltr in inventory:
                mapped[xsi_name] = (ltr, "rtl-flip")
            else:
                unmapped.append(xsi_name)
        else:
            unmapped.append(xsi_name)

    # Stage 2: upstream alias groups. A name with byte-identical artwork to
    # a mapped name inherits that mapping (alphabetically first such name).
    groups = content_groups()
    still_unmapped: list[str] = []
    for xsi_name in unmapped:
        digest = hashlib.sha256((XSI_DIR / xsi_name).read_bytes()).hexdigest()
        donor = next((n for n in groups[digest] if n in mapped), None)
        if donor is not None:
            source, method = mapped[donor]
            method = method.removeprefix("alias-")
            mapped[xsi_name] = (source, f"alias-{method}")
        else:
            still_unmapped.append(xsi_name)
    unmapped = still_unmapped

    rows = [
        (
            xsi_name,
            source,
            method,
            ",".join(f"{s}:{c}" for s, c in inventory[source]),
        )
        for xsi_name, (source, method) in sorted(mapped.items())
    ]

    MAPPING_TSV.parent.mkdir(parents=True, exist_ok=True)
    with MAPPING_TSV.open("w") as f:
        f.write("# xsi_name\tpapirus_name\tmethod\tcontexts\n")
        for row in rows:
            f.write("\t".join(row) + "\n")

    with UNMAPPED_TXT.open("w") as f:
        f.write("\n".join(unmapped) + "\n")

    copies = sum(1 for r in rows if r[2] == "copy")
    flips = sum(1 for r in rows if r[2] == "rtl-flip")
    aliases = sum(1 for r in rows if r[2].startswith("alias-"))
    total = len(names)
    print(f"upstream icon names : {total}")
    print(f"mapped (exact copy) : {copies}")
    print(f"mapped (rtl flip)   : {flips}")
    print(f"mapped (via alias)  : {aliases}")
    print(f"unmapped            : {len(unmapped)}")
    print(f"coverage            : {100 * len(rows) / total:.1f}%")
    print(f"\nwrote {MAPPING_TSV.relative_to(REPO)}")
    print(f"wrote {UNMAPPED_TXT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
