import csv
import hashlib
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

import build_report_data

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("generator", ROOT / "ML Model" / "Synthetic Data" / "generateData.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class GeneratorTests(unittest.TestCase):
    def test_all_mean_profiles_generate_valid_matrices(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("MondayMean", "SundayMean", "NewYearMean"):
                with self.subTest(profile=name):
                    output = Path(directory) / name
                    self.assertEqual(generator.generate(ROOT / "ML Model" / "Synthetic Data" / name, output), 144)
                    with output.open(newline="") as stream:
                        rows = list(csv.reader(stream))
                    self.assertEqual(len(rows), 144)
                    self.assertTrue(all(len(row) == 12 for row in rows))
                    self.assertTrue(all(math.isfinite(float(value)) and float(value) >= 0 for row in rows for value in row[2:]))

    def test_seed_controls_generation(self):
        source = ROOT / "ML Model" / "Synthetic Data" / "MondayMean"
        with tempfile.TemporaryDirectory() as directory:
            files = [Path(directory) / str(index) for index in range(3)]
            for output, seed in zip(files, (42, 42, 43)):
                generator.generate(source, output, seed)
            self.assertEqual(files[0].read_bytes(), files[1].read_bytes())
            self.assertNotEqual(files[0].read_bytes(), files[2].read_bytes())
            with self.assertRaises(FileExistsError):
                generator.generate(source, files[0])
        with self.assertRaises(ValueError):
            generator.generate(source, source)

    def test_invalid_profiles_fail_before_writing(self):
        for bad_row in ("0:00,0:10,nan", "0:00,0:10,-1", "0:00,0:10", "25:00,25:10,1", "0:00,0:20,1"):
            with self.subTest(row=bad_row), tempfile.TemporaryDirectory() as directory:
                source, output = Path(directory) / "input.csv", Path(directory) / "output.csv"
                source.write_text(bad_row + "\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    generator.generate(source, output)
                self.assertFalse(output.exists())


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "docs" / "report-data.js").read_text(encoding="utf-8").removeprefix("window.HEATMAP_DATA = ").rstrip(";\n"))

    def test_exported_counts_and_baselines(self):
        self.assertEqual(self.data["sequenceRows"], 4032)
        self.assertEqual(self.data["evaluationRows"], 1008)
        self.assertEqual(self.data["evaluationValues"], 10080)
        self.assertEqual(self.data["resourceUnits"], 492)
        self.assertEqual(self.data["driverRows"], 2)
        for actual, expected in zip(self.data["baselines"], (14.039365364670498, 19.006953057973554, 11.887464057980646)):
            self.assertAlmostEqual(actual["mae"], expected)

    def test_csv_download_matches_report(self):
        with (ROOT / "docs" / "profiles.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 4320)
        for row in rows:
            index = self.data["times"].index(row["time"])
            zone = next(zone for zone in self.data["zones"] if zone["name"] == row["zone"])
            demand = self.data["profiles"][row["scenario"]][index][zone["id"] - 1]
            self.assertEqual(float(row["synthetic_demand"]), demand)
            self.assertAlmostEqual(float(row["score"]), demand / zone["resources"])

    def test_original_sources_are_unchanged(self):
        for source in self.data["sources"]:
            with self.subTest(path=source["path"]):
                self.assertEqual(hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(), source["sha256"])

    def test_regeneration_is_deterministic(self):
        files = [ROOT / "docs" / name for name in ("report-data.js", "profiles.csv")]
        before = [path.read_bytes() for path in files]
        build_report_data.build()
        self.assertEqual(before, [path.read_bytes() for path in files])


if __name__ == "__main__":
    unittest.main()
