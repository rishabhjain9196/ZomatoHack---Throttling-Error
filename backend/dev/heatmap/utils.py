import csv
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCENARIOS = {
    "monday": "MondayData.csv",
    "sunday": "SundayData.csv",
    "new-year": "NewYearData.csv",
}
ZONE_COUNT = 10


def get_csv_data(scenario, at_time=None):
    if scenario not in SCENARIOS:
        raise ValueError("Choose monday, sunday or new-year.")
    if at_time is None:
        at_time = datetime.now(ZoneInfo("Asia/Kolkata")).time()
    # Preserve the original demo's next-interval lookup, including midnight rollover.
    minutes = ((at_time.hour * 60 + at_time.minute + 9) // 10 * 10) % 1440
    slot = f"{minutes // 60:02d}:{minutes % 60:02d}"
    profiles = {}
    with (DATA_DIR / SCENARIOS[scenario]).open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if len(row) != ZONE_COUNT + 2:
                raise ValueError("Each profile row must contain two times and ten zone values.")
            hour, minute = map(int, row[0].split(":"))
            if not 0 <= hour < 24 or minute not in range(0, 60, 10):
                raise ValueError("Profile times must be valid ten-minute intervals.")
            key = f"{hour:02d}:{minute:02d}"
            if key in profiles:
                raise ValueError(f"Duplicate profile interval: {key}.")
            values = [float(value) for value in row[2:]]
            if not all(math.isfinite(value) and value >= 0 for value in values):
                raise ValueError("Synthetic demand must be finite and non-negative.")
            profiles[key] = values
    if len(profiles) != 144:
        raise ValueError("A daily profile must contain all 144 ten-minute intervals.")
    return slot, profiles[slot]


def find_block(latitude, longitude, blocks):
    if not blocks:
        raise ValueError("Load the demo zones before requesting a heatmap.")
    return min(
        blocks,
        key=lambda block: (block.latitude - latitude) ** 2 + (block.longitude - longitude) ** 2,
    )
