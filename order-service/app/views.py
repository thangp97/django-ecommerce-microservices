from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Order, OrderItem
from .serializers import OrderSerializer
from .publisher import publish_order_created
import requests

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

class OrderListCreate(APIView):
    def get(self, request, customer_id=None):
        if customer_id:
            orders = Order.objects.all().filter(customer_id=customer_id).order_by('-created_at')
        else:
            orders = Order.objects.all().order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        customer_id = data.get("customer_id")
        items = data.get("items", [])
        total_price = float(data.get("total_price", 0))
        shipping_fee = float(data.get("shipping_fee", 0))
        grand_total = total_price + shipping_fee
        shipping_address = data.get("shipping_address", "Default Address")
        payment_method = data.get("payment_method", "cod")

        # Basic validation
        if not items:
            return Response({"error": "No items in order"}, status=400)

        import random
        import string
        tracking_number = "VN" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        # Saga Flow: Always start with 'pending'
        initial_status = 'pending'

        order = Order.objects.create(
            customer_id=customer_id,
            total_price=total_price,
            shipping_fee=shipping_fee,
            grand_total=grand_total,
            shipping_address=shipping_address,
            payment_method=payment_method,
            tracking_number=tracking_number,
            status=initial_status,
            payment_status='unpaid'
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product_id=item.get('product_id', item.get('book_id')),
                product_type=item.get('product_type', 'book'),
                quantity=item['quantity'],
                price=item['price']
            )
        
        # Publish event for Saga
        publish_order_created({
            "order_id": order.id,
            "customer_id": customer_id,
            "amount": grand_total,
            "payment_method": payment_method,
            "shipping_address": shipping_address,
            "items": items
        })

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=201)

class OrderDetail(APIView):
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

    def delete(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            # Only allow cancellation for pending or confirmed status
            if order.status not in ['pending', 'confirmed', 'paid']:
                return Response({"error": "Cannot cancel this order at current stage"}, status=400)
            
            # Rollback stock logic
            items = OrderItem.objects.filter(order=order)
            for item in items:
                try:
                    entry = PRODUCT_SERVICE_MAP.get(item.product_type)
                    if not entry:
                        print(f"Unknown product_type: {item.product_type}")
                        continue
                    base_url, plural = entry
                    requests.post(f"{base_url}/{plural}/{item.product_id}/restore-stock/",
                                  json={"quantity": item.quantity}, timeout=2)
                except Exception as e:
                    print(f"Error restoring stock: {e}")
            
            order.status = 'cancelled'
            order.save()
            return Response({"status": "cancelled", "message": "Order cancelled and stock restored."})
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            new_status = request.data.get("status")
            if new_status:
                order.status = new_status
                order.save()
            return Response({"status": "updated", "order_status": order.status})
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

