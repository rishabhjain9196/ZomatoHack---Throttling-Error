from datetime import time
from decimal import Decimal
import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from . import models, utils


class HeatmapTests(TestCase):
    fixtures = ["demo_blocks"]

    def setUp(self):
        self.client = APIClient()

    def post_location(self, driver=2, latitude=12.9279, longitude=77.6271):
        return self.client.post(
            "/heatmap/update_location",
            {"id": driver, "latitude": latitude, "longitude": longitude},
            format="json",
        )

    def test_time_slots_are_exact_and_wrap_at_midnight(self):
        for selected, expected in ((time(0, 0), "00:00"), (time(1, 1), "01:10"), (time(9, 50), "09:50"), (time(23, 59), "00:00")):
            with self.subTest(selected=selected):
                slot, values = utils.get_csv_data("monday", selected)
                self.assertEqual(slot, expected)
                self.assertEqual(len(values), 10)
        _, one = utils.get_csv_data("monday", time(1, 0))
        _, eleven = utils.get_csv_data("monday", time(11, 0))
        self.assertNotEqual(one, eleven)

    def test_new_year_rows_are_looked_up_by_label_not_position(self):
        slot, values = utils.get_csv_data("new-year", time(12, 0))
        self.assertEqual(slot, "12:00")
        self.assertAlmostEqual(values[0], 177.8283236650826)

    def test_heatmap_exposes_structured_and_legacy_shapes(self):
        for scenario in utils.SCENARIOS:
            with self.subTest(scenario=scenario):
                response = self.client.get("/heatmap/get_heatmap", {"scenario": scenario, "time": "09:10"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["time"], "09:10")
                self.assertEqual([zone["id"] for zone in response.data["zones"]], list(range(1, 11)))
                self.assertEqual(len(response.data["response"].strip(",").split(",")), 30)

    def test_bad_queries_return_validation_errors(self):
        for query in ({"scenario": "../../data"}, {"time": "25:60"}, {"time": "garbage"}):
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/heatmap/get_heatmap", query).status_code, 400)

    def test_same_block_does_not_change_resource_units(self):
        before = list(models.Block.objects.order_by("id").values_list("resources", flat=True))
        response = self.post_location(latitude=12.97191, longitude=77.64121)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(before, list(models.Block.objects.order_by("id").values_list("resources", flat=True)))
        self.assertEqual(models.DriverLocation.objects.get(pk=2).latitude, Decimal("12.9719"))

    def test_cross_block_move_conserves_resource_units(self):
        response = self.post_location()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.Block.objects.get(pk=1).resources, 94)
        self.assertEqual(models.Block.objects.get(pk=2).resources, 89)
        self.assertEqual(sum(models.Block.objects.values_list("resources", flat=True)), 492)
        self.post_location()
        self.assertEqual(models.Block.objects.get(pk=1).resources, 94)

    def test_new_driver_retains_requested_id_and_adds_supply_once(self):
        response = self.post_location(driver=42)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["id"], 42)
        self.assertEqual(models.Block.objects.get(pk=1).resources, 94)
        self.assertEqual(self.post_location(driver=42).status_code, 200)
        self.assertEqual(models.Block.objects.get(pk=1).resources, 94)

    def test_original_special_driver_weight_is_preserved(self):
        self.assertEqual(self.post_location(driver=1).status_code, 200)
        self.assertEqual(models.Block.objects.get(pk=9).resources, 28)
        self.assertEqual(models.Block.objects.get(pk=1).resources, 91)

    def test_insufficient_supply_is_rejected_without_partial_changes(self):
        models.Block.objects.filter(pk=2).update(resources=0)
        response = self.post_location()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(models.Block.objects.get(pk=1).resources, 84)
        self.assertEqual(models.DriverLocation.objects.get(pk=2).latitude, Decimal("12.9719"))

    def test_zero_supply_is_explicit_and_does_not_mutate_database(self):
        for resources in (0, -2):
            with self.subTest(resources=resources):
                models.Block.objects.filter(pk=1).update(resources=resources)
                response = self.client.get("/heatmap/get_heatmap", {"time": "12:00"})
                zone = response.data["zones"][0]
                self.assertTrue(zone["denominator_floored"])
                self.assertEqual(zone["score"], zone["demand"])
                self.assertEqual(models.Block.objects.get(pk=1).resources, resources)

    def test_missing_zones_are_an_explicit_setup_error(self):
        models.Block.objects.all().delete()
        self.assertEqual(self.post_location().status_code, 503)
        self.assertEqual(self.client.get("/heatmap/get_heatmap").status_code, 503)

    def test_partial_zone_configuration_is_rejected(self):
        models.Block.objects.filter(pk=10).delete()
        self.assertEqual(self.post_location().status_code, 503)
        self.assertEqual(self.client.get("/heatmap/get_heatmap").status_code, 503)

    def test_invalid_profile_files_are_rejected(self):
        with (utils.DATA_DIR / "MondayData.csv").open(newline="", encoding="utf-8") as stream:
            original = list(csv.reader(stream))
        for corruption in ("short-row", "duplicate", "missing", "non-finite", "negative", "bad-time"):
            with self.subTest(corruption=corruption), TemporaryDirectory() as directory:
                rows = [row[:] for row in original]
                if corruption == "short-row":
                    rows[0].pop()
                elif corruption == "duplicate":
                    rows[1] = rows[0]
                elif corruption == "missing":
                    rows.pop()
                elif corruption == "non-finite":
                    rows[0][2] = "nan"
                elif corruption == "negative":
                    rows[0][2] = "-1"
                else:
                    rows[0][0] = "24:00"
                with (Path(directory) / "MondayData.csv").open("w", newline="", encoding="utf-8") as stream:
                    csv.writer(stream).writerows(rows)
                with patch.object(utils, "DATA_DIR", Path(directory)), self.assertRaises(ValueError):
                    utils.get_csv_data("monday", time(12, 0))

    def test_missing_profile_returns_service_error_and_logs(self):
        with patch("heatmap.utils.get_csv_data", side_effect=FileNotFoundError("Missing synthetic profile")):
            with self.assertLogs("heatmap.views", level="ERROR"):
                self.assertEqual(self.client.get("/heatmap/get_heatmap").status_code, 503)

    def test_invalid_location_does_not_modify_data(self):
        for payload in ({}, {"id": 2, "latitude": 91, "longitude": 77}, {"id": -1, "latitude": 12, "longitude": 77}, {"id": 2, "latitude": "NaN", "longitude": 77}):
            with self.subTest(payload=payload):
                response = self.client.post("/heatmap/update_location", payload, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertEqual(models.DriverLocation.objects.count(), 2)

    def test_unimplemented_inference_does_not_return_fake_success(self):
        self.assertEqual(self.client.get("/heatmap/get_next_data").status_code, 501)
