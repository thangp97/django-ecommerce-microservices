from rest_framework import serializers
from .models import Cosmetic


class CosmeticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cosmetic
        fields = '__all__'
