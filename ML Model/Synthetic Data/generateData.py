import argparse
import csv
import math
import random
from pathlib import Path


def generate(input_path, output_path, seed=42):
    if input_path.resolve() == output_path.resolve():
        raise ValueError("The output must not overwrite the input profile.")
    if output_path.exists():
        raise FileExistsError("Choose a new output file to preserve existing data.")
    random_source = random.Random(seed)
    rows = []
    intervals = set()
    with input_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if len(row) < 3:
                raise ValueError("Each row needs a start time, end time and demand mean.")
            start_hour, start_minute = map(int, row[0].split(":"))
            end_hour, end_minute = map(int, row[1].split(":"))
            if not all(0 <= hour < 24 and minute in range(0, 60, 10) for hour, minute in ((start_hour, start_minute), (end_hour, end_minute))):
                raise ValueError("Profile times must be valid ten-minute boundaries.")
            start = start_hour * 60 + start_minute
            if start in intervals or (end_hour * 60 + end_minute) != (start + 10) % 1440:
                raise ValueError("Intervals must be unique and ten minutes long.")
            intervals.add(start)
            mean = float(row[2])
            if not math.isfinite(mean) or mean < 0:
                raise ValueError("Demand means must be finite and non-negative.")
            rows.append(row[:2] + [max(0, random_source.gauss(mean, mean * 0.1)) for _ in range(10)])
    if len(rows) != 144:
        raise ValueError("The input must contain 144 ten-minute intervals.")
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a seeded synthetic daily profile.")
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("MondayMean"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(f"Wrote {generate(args.input, args.output, args.seed)} intervals to {args.output}.")
