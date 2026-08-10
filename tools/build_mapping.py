"""Build the xsi -> Papirus mapping table (exact matches only).

For every icon name shipped by upstream xapp-symbolic-icons, look for an
exact-name equivalent in the Papirus symbolic icon set:

  xsi-<name>-symbolic.svg      -> <name>-symbolic.svg
  xsi-<name>-symbolic-rtl.svg  -> <name>-symbolic-rtl.svg   (exact rtl)
                               or <name>-symbolic.svg        (mirrored)

Hand-curated mappings in mapping/overrides.tsv take precedence over all
automatic stages; they hold the few cases where naming conventions disagree
and the right match was verified by looking at the artwork.

Names that don't match directly are resolved through upstream's own
equivalence data -- still no artistic judgment on our side:

* xsi-adwaita-symbolic.info: upstream's adwaita-name -> xsi-name rename
  table (used by their migration script). If Papirus has the old adwaita
  name, upstream itself declared it equivalent.
* xapp- prefix: XSI succeeded the old xapp-* icon names, which Papirus
  already ships (xapp-foo-symbolic -> xsi-foo-symbolic).
* alias groups: upstream ships byte-identical artwork under multiple
  names; any name in a group inherits its mapped sibling's source.

No fuzzy or concept matching is performed. Unmapped names are written to
mapping/unmapped.txt for a later pass.

Output: mapping/mapping.tsv with columns:
  xsi_name   papirus_name   method   contexts(size:context,...)

where method is copy | rtl-flip, optionally prefixed by its origin:
manual- | adwaita- | xapp- | alias-.
"""

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
XSI_DIR = REPO / "vendor" / "xapp-symbolic-icons" / "icons" / "symbolic"
XSI_INFO = (
    REPO / "vendor" / "xapp-symbolic-icons" / "icons" / "xsi-adwaita-symbolic.info"
)
PAPIRUS = REPO / "vendor" / "papirus-icon-theme" / "Papirus"

# Real (non-symlink) symbolic directories in the Papirus theme. Other sizes
# (32x32, symbolic-up-to-20, @2x) are symlinks to these and need no output.
SIZES = ("16x16", "22x22", "24x24")

MAPPING_TSV = REPO / "mapping" / "mapping.tsv"
OVERRIDES_TSV = REPO / "mapping" / "overrides.tsv"
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
                inventory.setdefault(svg.name, []).append((size, context_dir.name))
    return inventory


def xsi_names() -> list[str]:
    if not XSI_DIR.is_dir():
        sys.exit(f"error: {XSI_DIR} not found (init submodules first)")
    return sorted(p.name for p in XSI_DIR.glob("*.svg"))


def overrides() -> dict[str, str]:
    """Read hand-curated xsi_name -> papirus_name mappings."""
    result: dict[str, str] = {}
    if not OVERRIDES_TSV.is_file():
        return result
    for line in OVERRIDES_TSV.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        xsi_name, papirus_name = line.split("\t")
        result[xsi_name] = papirus_name
    return result


def adwaita_renames() -> dict[str, list[str]]:
    """Map xsi base name -> [old adwaita names], from upstream's rename table.

    Lines look like:  system-shutdown # actions # shutdown
    Several old names may map to the same xsi name; file order is kept.
    """
    renames: dict[str, list[str]] = {}
    for line in XSI_INFO.read_text().splitlines():
        parts = [p.strip() for p in line.split("#")]
        if len(parts) != 3 or not parts[0]:
            continue
        old, _context, new = parts
        renames.setdefault(new, []).append(old)
    return renames


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

    # Stage 0: hand-curated overrides (verified against the artwork).
    manual = overrides()
    for xsi_name, papirus_name in manual.items():
        if xsi_name not in names:
            sys.exit(f"error: override {xsi_name} is not an upstream icon")
        if papirus_name not in inventory:
            sys.exit(f"error: override target {papirus_name} not in Papirus")
        mapped[xsi_name] = (papirus_name, "manual-copy")

    # Stage 1: exact name matches (with rtl fallback to mirroring).
    for xsi_name in names:
        assert xsi_name.startswith("xsi-"), xsi_name
        if xsi_name in mapped:
            continue
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

    # Stage 2: upstream rename data. Try, in order:
    #   a. old adwaita names from xsi-adwaita-symbolic.info (file order)
    #   b. the old xapp-* name (xsi-foo <- xapp-foo)
    # Each candidate is used directly if Papirus has it; -rtl names fall
    # back to mirroring the candidate's LTR icon, as in stage 1.
    renames = adwaita_renames()
    still_unmapped: list[str] = []
    for xsi_name in unmapped:
        base = xsi_name[len("xsi-") :]
        is_rtl = base.endswith("-symbolic-rtl.svg")
        stem = base.removesuffix("-rtl.svg" if is_rtl else ".svg")
        stem = stem.removesuffix("-symbolic")

        candidates = [f"{old}-symbolic" for old in renames.get(stem, [])]
        candidates.append(f"xapp-{stem}-symbolic")

        for origin, candidate in [
            ("adwaita", c) if not c.startswith("xapp-") else ("xapp", c)
            for c in candidates
        ]:
            if is_rtl and f"{candidate}-rtl.svg" in inventory:
                mapped[xsi_name] = (f"{candidate}-rtl.svg", f"{origin}-copy")
                break
            if f"{candidate}.svg" in inventory:
                method = "rtl-flip" if is_rtl else "copy"
                mapped[xsi_name] = (f"{candidate}.svg", f"{origin}-{method}")
                break
        else:
            still_unmapped.append(xsi_name)
    unmapped = still_unmapped

    # Stage 3: upstream alias groups. A name with byte-identical artwork to
    # a mapped name inherits that mapping (alphabetically first such name).
    groups = content_groups()
    still_unmapped = []
    for xsi_name in unmapped:
        digest = hashlib.sha256((XSI_DIR / xsi_name).read_bytes()).hexdigest()
        donor = next((n for n in groups[digest] if n in mapped), None)
        if donor is not None:
            source, method = mapped[donor]
            # keep only the base method; origin becomes "alias"
            method = (
                method.split("-", 1)[1]
                if method.startswith(("manual-", "alias-", "adwaita-", "xapp-"))
                else method
            )
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
    manual = sum(1 for r in rows if r[2].startswith("manual-"))
    adwaita = sum(1 for r in rows if r[2].startswith("adwaita-"))
    xapp = sum(1 for r in rows if r[2].startswith("xapp-"))
    aliases = sum(1 for r in rows if r[2].startswith("alias-"))
    total = len(names)
    print(f"upstream icon names   : {total}")
    print(f"mapped (exact copy)   : {copies}")
    print(f"mapped (rtl flip)     : {flips}")
    print(f"mapped (manual)       : {manual}")
    print(f"mapped (adwaita name) : {adwaita}")
    print(f"mapped (xapp name)    : {xapp}")
    print(f"mapped (via alias)    : {aliases}")
    print(f"unmapped              : {len(unmapped)}")
    print(f"coverage              : {100 * len(rows) / total:.1f}%")
    print(f"\nwrote {MAPPING_TSV.relative_to(REPO)}")
    print(f"wrote {UNMAPPED_TXT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
