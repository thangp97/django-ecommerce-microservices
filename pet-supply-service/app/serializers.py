from rest_framework import serializers
from .models import PetSupply


class PetSupplySerializer(serializers.ModelSerializer):
    class Meta:
        model = PetSupply
        fields = '__all__'
