from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
import requests

# Map product_type -> (service URL, URL plural). Phải khớp với api-gateway PRODUCT_SERVICE_MAP.
PRODUCT_SERVICE_MAP = {
    "book":       ("http://book-service:8000",       "books"),
    "clothe":     ("http://clothe-service:8000",     "clothes"),
    "electronic": ("http://electronic-service:8000", "electronics"),
    "food":       ("http://food-service:8000",       "foods"),
    "toy":        ("http://toy-service:8000",        "toys"),
    "furniture":  ("http://furniture-service:8000",  "furnitures"),
    "cosmetic":   ("http://cosmetic-service:8000",   "cosmetics"),
    "sport":      ("http://sport-service:8000",      "sports"),
    "stationery": ("http://stationery-service:8000", "stationeries"),
    "appliance":  ("http://appliance-service:8000",  "appliances"),
    "jewelry":    ("http://jewelry-service:8000",    "jewelries"),
    "pet-supply": ("http://pet-supply-service:8000", "pet-supplies"),
}


class CartCreate(APIView):
    def post(self, request):
        serializer = CartSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)


class AddCartItem(APIView):
    def post(self, request):
        cart_id = request.data.get("cart")
        # Hỗ trợ cả tên mới (product_id) và legacy (book_id)
        product_id = request.data.get("product_id") or request.data.get("book_id")
        product_type = request.data.get("product_type", "book")
        quantity = request.data.get("quantity")

        try:
            cart_id = int(cart_id)
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"error": "Invalid cart, product_id or quantity"}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response({"error": "Quantity must be greater than 0"}, status=status.HTTP_400_BAD_REQUEST)

        if not Cart.objects.filter(id=cart_id).exists():
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        entry = PRODUCT_SERVICE_MAP.get(product_type)
        if not entry:
            return Response({"error": f"Unknown product_type '{product_type}'"}, status=status.HTTP_400_BAD_REQUEST)
        base_url, plural = entry

        try:
            r = requests.get(f"{base_url}/{plural}/{product_id}/", timeout=3)
            if r.status_code != 200:
                return Response({"error": f"{product_type} not found"}, status=status.HTTP_404_NOT_FOUND)

            item_data = r.json()
            available = int(item_data.get("stock", 0) or 0)
            if available < quantity:
                return Response({"error": "Insufficient stock"}, status=status.HTTP_400_BAD_REQUEST)

            existing = CartItem.objects.filter(
                cart_id=cart_id, product_type=product_type, product_id=product_id
            ).first()
            if existing:
                merged_quantity = existing.quantity + quantity
                if available < merged_quantity:
                    return Response({"error": "Insufficient stock for requested quantity"}, status=status.HTTP_400_BAD_REQUEST)
                existing.quantity = merged_quantity
                existing.save(update_fields=["quantity"])
                return Response(CartItemSerializer(existing).data, status=status.HTTP_200_OK)

        except requests.exceptions.RequestException:
            # Dependency down → cho phép degraded mode
            pass

        serializer = CartItemSerializer(data={
            "cart": cart_id,
            "product_id": product_id,
            "product_type": product_type,
            "quantity": quantity,
        })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteCartItem(APIView):
    def delete(self, request, cart_id, product_type, product_id):
        try:
            CartItem.objects.filter(
                cart_id=cart_id, product_type=product_type, product_id=product_id
            ).delete()
            return Response({"message": "Item removed from cart"})
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class ClearCart(APIView):
    def delete(self, request, customer_id):
        try:
            cart = Cart.objects.get(customer_id=customer_id)
            CartItem.objects.filter(cart=cart).delete()
            return Response({"message": "Cart cleared successfully"})
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CartView(APIView):
    def get(self, request, customer_id):
        try:
            cart, _ = Cart.objects.get_or_create(customer_id=customer_id)
            items = CartItem.objects.filter(cart=cart)
            serializer = CartItemSerializer(items, many=True)
            return Response({"cart_id": cart.id, "items": serializer.data})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
