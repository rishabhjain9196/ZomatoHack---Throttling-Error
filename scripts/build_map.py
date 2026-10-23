"""Cache one attributed Bengaluru basemap for the static report."""

import io
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def build():
    zoom, width, height = 12, 900, 700
    longitude, latitude = 77.64, 12.935
    left = round((longitude + 180) / 360 * 2 ** zoom * 256 - width / 2)
    top = round((1 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2 * 2 ** zoom * 256 - height / 2)
    canvas = Image.new("RGB", (width, height))
    for x in range(left // 256, (left + width - 1) // 256 + 1):
        for y in range(top // 256, (top + height - 1) // 256 + 1):
            url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
            request = Request(url, headers={"User-Agent": "Throttling-Error-Report/1.0 (+https://github.com/rishabhjain9196/ZomatoHack---Throttling-Error)"})
            with urlopen(request, timeout=30) as response:
                tile = Image.open(io.BytesIO(response.read())).convert("RGB")
                canvas.paste(tile, (x * 256 - left, y * 256 - top))
    canvas.save(DOCS / "bengaluru.webp", quality=88)
    metadata = {"zoom": zoom, "width": width, "height": height, "left": left, "top": top}
    (DOCS / "map.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {width} x {height} cached basemap.")


if __name__ == "__main__":
    build()
