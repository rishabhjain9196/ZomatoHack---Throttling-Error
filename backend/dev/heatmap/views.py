import logging

from django.db import transaction
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import models, utils
from .serializers import DriverLocationSerializer, HeatmapQuerySerializer

logger = logging.getLogger(__name__)


def index(request):
    return JsonResponse({"status": "ok", "mode": "local synthetic-data demo"})


class update_location(APIView):
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        return Response({"detail": "POST id, latitude and longitude to update a demo driver."})

    @transaction.atomic
    def post(self, request):
        serializer = DriverLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        blocks = list(models.Block.objects.select_for_update().order_by("id"))
        if [block.pk for block in blocks] != list(range(1, utils.ZONE_COUNT + 1)):
            return Response({"detail": "Load the ten original demo zones before updating locations."}, status=503)
        new_block = utils.find_block(data["latitude"], data["longitude"], blocks)
        driver = models.DriverLocation.objects.select_for_update().filter(pk=data["id"]).first()
        # These are resource weights from the hackathon demonstration, not fleet counts.
        weight = 7 if data["id"] == 1 else 10
        created = driver is None
        if created:
            driver = models.DriverLocation(id=data["id"])
            new_block.resources += weight
            new_block.save(update_fields=["resources"])
            message = f"Registered in {new_block.name}."
        else:
            old_block = utils.find_block(driver.latitude, driver.longitude, blocks)
            if old_block.pk != new_block.pk:
                if old_block.resources < weight:
                    return Response(
                        {"detail": "The origin zone has insufficient demo resource units."},
                        status=status.HTTP_409_CONFLICT,
                    )
                old_block.resources -= weight
                new_block.resources += weight
                old_block.save(update_fields=["resources"])
                new_block.save(update_fields=["resources"])
            message = f"You moved from {old_block.name} to {new_block.name}."
        driver.latitude = data["latitude"]
        driver.longitude = data["longitude"]
        driver.save()
        return Response(
            {"id": driver.pk, "lat": driver.latitude, "lon": driver.longitude, "toast_text": message},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class get_heatmap(APIView):
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        serializer = HeatmapQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data
        blocks = list(models.Block.objects.order_by("id"))
        if [block.pk for block in blocks] != list(range(1, utils.ZONE_COUNT + 1)):
            return Response({"detail": "Load the ten original demo zones in ID order."}, status=503)
        try:
            slot, demand = utils.get_csv_data(query["scenario"], query.get("time"))
        except (OSError, ValueError) as error:
            logger.exception("The synthetic demand profile could not be read.")
            return Response({"detail": str(error)}, status=503)
        zones = []
        for block, value in zip(blocks, demand):
            zones.append({
                "id": block.pk,
                "name": block.name,
                "latitude": float(block.latitude),
                "longitude": float(block.longitude),
                "demand": value,
                "resource_units": block.resources,
                "score": value / max(block.resources, 1),
                "denominator_floored": block.resources <= 0,
            })
        coordinates = [value for zone in zones for value in (zone["latitude"], zone["longitude"])]
        legacy = coordinates + [zone["score"] for zone in zones]
        return Response({
            "scenario": query["scenario"],
            "time": slot,
            "source": "synthetic CSV profile; not live LSTM inference",
            "zones": zones,
            "response": ",".join(map(str, legacy)) + ",",
        })


class get_next_data(APIView):
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        return Response(
            {"detail": "Live model inference is not connected. Use get_heatmap for the CSV demo."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
