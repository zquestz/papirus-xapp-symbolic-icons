"""Generate the Papirus xsi icon set from mapping/mapping.tsv.

Reads the mapping produced by build_mapping.py and populates:

  icons/Papirus/<size>/symbolic/<context>/xsi-<name>.svg

Methods:
  copy      -- byte-for-byte copy of the Papirus source icon
  rtl-flip  -- horizontally mirrored copy (for -rtl variants Papirus lacks)

Methods may carry an origin prefix (manual- | adwaita- | xapp- | alias-)
recording how the mapping was derived; generation is identical either way.

The output mirrors the Papirus theme layout so installation is a plain
directory merge. Only the real symbolic dirs (16x16, 22x22, 24x24) are
populated; Papirus's own symlinks (32x32, symbolic-up-to-20, @2x) extend
them to the remaining lookup sizes automatically.
"""

import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAPIRUS = REPO / "vendor" / "papirus-icon-theme" / "Papirus"
MAPPING_TSV = REPO / "mapping" / "mapping.tsv"
OUT = REPO / "icons" / "Papirus"

SVG_NS = "http://www.w3.org/2000/svg"


def flip_svg(source: Path, dest: Path) -> None:
    """Write a horizontally mirrored copy of an SVG icon."""
    ET.register_namespace("", SVG_NS)
    tree = ET.parse(source)
    root = tree.getroot()

    width = root.get("width")
    if width is None:
        viewbox = root.get("viewBox", "").split()
        if len(viewbox) != 4:
            sys.exit(f"error: cannot determine width of {source}")
        width = viewbox[2]

    group = ET.Element(f"{{{SVG_NS}}}g")
    group.set("transform", f"matrix(-1,0,0,1,{width},0)")
    children = list(root)
    for child in children:
        root.remove(child)
        group.append(child)
    root.append(group)

    tree.write(dest, encoding="unicode", xml_declaration=False)


def main() -> None:
    if not MAPPING_TSV.is_file():
        sys.exit("error: mapping/mapping.tsv not found (run build_mapping.py)")

    if OUT.exists():
        shutil.rmtree(OUT)

    copies = flips = files = 0
    for line in MAPPING_TSV.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        xsi_name, papirus_name, method, contexts = line.split("\t")
        for prefix in ("manual-", "adwaita-", "xapp-", "alias-"):
            method = method.removeprefix(prefix)

        for entry in contexts.split(","):
            size, context = entry.split(":")
            source = PAPIRUS / size / "symbolic" / context / papirus_name
            dest_dir = OUT / size / "symbolic" / context
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / xsi_name

            if method == "copy":
                shutil.copyfile(source, dest)
            elif method == "rtl-flip":
                flip_svg(source, dest)
            else:
                sys.exit(f"error: unknown method {method!r} for {xsi_name}")
            files += 1

        if method == "copy":
            copies += 1
        else:
            flips += 1

    print(f"icons generated : {copies + flips} ({copies} copies, {flips} rtl flips)")
    print(f"files written   : {files}")
    print(f"output          : {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
