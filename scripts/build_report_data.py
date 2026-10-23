"""Export reproducible report data from the original hackathon artifacts."""

import csv
import hashlib
import json
import math
import sqlite3
from html import escape
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PROFILES = {"monday": "MondayData.csv", "sunday": "SundayData.csv", "new-year": "NewYearData.csv"}


def read_matrix(path, width):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = [[float(value) for value in row] for row in csv.reader(stream)]
    if not rows or any(len(row) != width or not all(math.isfinite(value) and value >= 0 for value in row) for row in rows):
        raise ValueError(f"Invalid numeric matrix: {path}")
    return rows


def write_cover(data):
    map_info = data["map"]
    demand = data["profiles"]["monday"][111]
    scores = [value / zone["resources"] for value, zone in zip(demand, data["zones"])]
    points = []
    for zone, score in zip(data["zones"], scores):
        x = 660 + (((zone["lon"] + 180) / 360 * 2 ** map_info["zoom"] * 256 - map_info["left"]) / map_info["width"]) * 470
        y = 130 + (((1 - math.asinh(math.tan(math.radians(zone["lat"]))) / math.pi) / 2 * 2 ** map_info["zoom"] * 256 - map_info["top"]) / map_info["height"]) * 380
        radius = 8 + 18 * math.sqrt(score / max(scores))
        points.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="#e28d67" fill-opacity=".8"/><text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" fill="#17343b" font-size="14">{zone["id"]}</text>')
    cover = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">
<title id="title">Demand-Supply Workforce Heatmaps in 2019</title>
<desc id="desc">Team Throttling-Error placed third nationally. The diagram shows ten archived Bengaluru zone coordinates, sized by synthetic demand per resource unit on Monday at 18:30.</desc>
<rect width="1200" height="630" fill="#17343b"/><rect x="630" y="65" width="525" height="490" rx="22" fill="#e8ede7"/>
<g font-family="Arial,sans-serif"><text x="55" y="90" font-size="15" letter-spacing="2" fill="#f6b498">ZOMATO HACKANOODLE / 2019</text>
<text x="55" y="170" font-size="54" fill="white">Where should</text><text x="55" y="232" font-size="54" fill="white">the workforce</text><text x="55" y="294" font-size="54" fill="white">move?</text>
<text x="55" y="365" font-size="20" fill="#d5e3df">Our team placed third nationally</text><text x="55" y="396" font-size="20" fill="#d5e3df">and presented to Deepinder Goyal.</text>
<text x="55" y="476" font-size="30" fill="#f6b498">10 zones / 3 scenarios / 28 days</text>
<text x="55" y="514" font-size="16" fill="#d5e3df">This is synthetic data, not a live fleet.</text>
<text x="660" y="105" font-size="17" fill="#17343b">Bengaluru zone coordinates</text>
{''.join(points)}
<text x="660" y="530" font-size="14" fill="#17343b">Circle size shows demand per resource unit at 18:30.</text>
<text x="55" y="595" font-size="14" fill="#d5e3df">{escape("Team 7: Abhirup Mondal, Pooja Agarwal, Rishabh Jain and Sanket Jain.")}</text></g></svg>'''
    (DOCS / "cover.svg").write_text(cover + "\n", encoding="utf-8")


def build():
    DOCS.mkdir(exist_ok=True)
    database = ROOT / "backend" / "dev" / "db.sqlite3"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        zones = [
            {"id": row[0], "name": row[1], "lat": row[2], "lon": row[3], "resources": row[4]}
            for row in connection.execute("SELECT id,name,latitude,longitude,resources FROM heatmap_block ORDER BY id")
        ]
        drivers = list(connection.execute("SELECT id,latitude,longitude FROM heatmap_driverlocation ORDER BY id"))
    if [zone["id"] for zone in zones] != list(range(1, 11)):
        raise ValueError("The original ten-zone order is required.")
    times = [f"{minute // 60:02d}:{minute % 60:02d}" for minute in range(0, 1440, 10)]
    profiles = {}
    inputs = [database]
    for scenario, filename in PROFILES.items():
        path = ROOT / "backend" / "dev" / "data" / filename
        inputs.append(path)
        values = {}
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.reader(stream):
                hour, minute = map(int, row[0].split(":"))
                key = f"{hour:02d}:{minute:02d}"
                numbers = [float(value) for value in row[2:]]
                if key in values or len(numbers) != 10 or not all(math.isfinite(value) and value >= 0 for value in numbers):
                    raise ValueError(f"Invalid or duplicate profile row: {path}")
                values[key] = numbers
        if set(values) != set(times):
            raise ValueError(f"Missing or invalid intervals: {path}")
        profiles[scenario] = [values[time] for time in times]
    sequence_path = ROOT / "ML Model" / "SyntheticData2.csv"
    inputs.append(sequence_path)
    sequence = read_matrix(sequence_path, 10)
    if len(sequence) != 28 * 144:
        raise ValueError("The report expects the original 28-day training sequence.")
    test_start = 21 * 144
    baselines = []
    for label, lag in (("Previous interval", 1), ("Previous day", 144), ("Previous week", 1008)):
        errors = [
            abs(sequence[index][zone] - sequence[index - lag][zone])
            for index in range(test_start, len(sequence)) for zone in range(10)
        ]
        baselines.append({"name": label, "lag": lag, "mae": mean(errors)})
    daily = [sum(sum(row) for row in sequence[start:start + 144]) for start in range(0, len(sequence), 144)]
    data = {
        "projectYear": 2019,
        "reviewYear": 2026,
        "map": json.loads((DOCS / "map.json").read_text(encoding="utf-8")),
        "zones": zones,
        "times": times,
        "profiles": profiles,
        "dailyTotals": daily,
        "baselines": baselines,
        "sequenceRows": len(sequence),
        "evaluationRows": len(sequence) - test_start,
        "evaluationValues": (len(sequence) - test_start) * 10,
        "driverRows": len(drivers),
        "resourceUnits": sum(zone["resources"] for zone in zones),
        "sources": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in inputs
        ],
    }
    (DOCS / "report-data.js").write_text("window.HEATMAP_DATA = " + json.dumps(data, separators=(",", ":"), allow_nan=False) + ";\n", encoding="utf-8")
    write_cover(data)
    with (DOCS / "profiles.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["scenario", "time", "zone", "latitude", "longitude", "synthetic_demand", "demo_resource_units", "score"])
        for scenario, rows in profiles.items():
            for time, row in zip(times, rows):
                for zone, demand in zip(zones, row):
                    writer.writerow([scenario, time, zone["name"], zone["lat"], zone["lon"], demand, zone["resources"], demand / max(zone["resources"], 1)])
    fixtures = [
        {"model": "heatmap.block", "pk": zone["id"], "fields": {
            "name": zone["name"], "latitude": str(zone["lat"]), "longitude": str(zone["lon"]), "resources": zone["resources"], "orders": 0,
        }}
        for zone in zones
    ]
    fixtures.extend(
        {"model": "heatmap.driverlocation", "pk": row[0], "fields": {"name": "Alex", "latitude": str(row[1]), "longitude": str(row[2])}}
        for row in drivers
    )
    fixture_dir = ROOT / "backend" / "dev" / "heatmap" / "fixtures"
    fixture_dir.mkdir(exist_ok=True)
    (fixture_dir / "demo_blocks.json").write_text(json.dumps(fixtures, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "sequence_rows": len(sequence), "zones": len(zones), "profile_rows": sum(len(rows) for rows in profiles.values()),
        "resource_units": data["resourceUnits"], "baselines": baselines,
    }, indent=2))
    return data


if __name__ == "__main__":
    build()
