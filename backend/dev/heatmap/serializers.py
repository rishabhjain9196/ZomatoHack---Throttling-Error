from rest_framework import serializers
import math
from decimal import Decimal

from .utils import SCENARIOS


class DriverLocationSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-99.9999, max_value=99.9999)

    def validate(self, attrs):
        for name in ("latitude", "longitude"):
            if not math.isfinite(attrs[name]):
                raise serializers.ValidationError({name: "Use a finite coordinate."})
            attrs[name] = Decimal(str(attrs[name])).quantize(Decimal("0.0001"))
        return attrs


class HeatmapQuerySerializer(serializers.Serializer):
    scenario = serializers.ChoiceField(choices=tuple(SCENARIOS), default="new-year")
    time = serializers.TimeField(input_formats=["%H:%M"], required=False)