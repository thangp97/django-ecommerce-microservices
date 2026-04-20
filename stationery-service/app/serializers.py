from rest_framework import serializers
from .models import Stationery


class StationerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Stationery
        fields = '__all__'
