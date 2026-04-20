from rest_framework import serializers
from .models import Cart, CartItem


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    # Alias để backward-compat với gateway cũ đang đọc `book_id`.
    book_id = serializers.IntegerField(source='product_id', read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product_id', 'product_type', 'quantity', 'book_id']
