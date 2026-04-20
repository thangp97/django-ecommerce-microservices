from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    # Alias cho backward-compat với gateway cũ đang đọc `book_id`.
    book_id = serializers.IntegerField(source='product_id', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product_id', 'product_type', 'quantity', 'price', 'book_id']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
