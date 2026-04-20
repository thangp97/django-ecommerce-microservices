from rest_framework import serializers
from .models import Jewelry


class JewelrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Jewelry
        fields = '__all__'
