import pika
import json
import os
import sys
import django

sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'order_service.settings')
django.setup()

from app.models import Order
import requests

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq')

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


def callback_success(ch, method, properties, body):
    data = json.loads(body)
    order_id = data.get('order_id')
    try:
        order = Order.objects.get(id=order_id)
        order.status = 'confirmed'
        order.save()
        print(f"Order {order_id} confirmed by Saga success")
    except Order.DoesNotExist:
        pass
    ch.basic_ack(delivery_tag=method.delivery_tag)


def callback_failed(ch, method, properties, body):
    data = json.loads(body)
    order_id = data.get('order_id')
    reason = data.get('reason')
    try:
        order = Order.objects.get(id=order_id)
        if order.status != 'cancelled':
            order.status = 'cancelled'
            order.save()
            print(f"Order {order_id} cancelled due to Saga failure: {reason}")

            # Compensation: restore stock cho từng item theo product_type
            for item in order.items.all():
                entry = PRODUCT_SERVICE_MAP.get(item.product_type)
                if not entry:
                    print(f"Unknown product_type '{item.product_type}' cho item {item.id}")
                    continue
                base_url, plural = entry
                try:
                    requests.post(
                        f"{base_url}/{plural}/{item.product_id}/restore-stock/",
                        json={"quantity": item.quantity},
                        timeout=3,
                    )
                    print(f"Restored stock: {item.product_type}#{item.product_id} qty={item.quantity}")
                except Exception as e:
                    print(f"Failed to restore stock for {item.product_type}#{item.product_id}: {e}")

    except Order.DoesNotExist:
        pass
    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consuming():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue='shipping_reserved_queue', durable=True)
    channel.basic_consume(queue='shipping_reserved_queue', on_message_callback=callback_success)

    channel.queue_declare(queue='payment_failed_queue', durable=True)
    channel.basic_consume(queue='payment_failed_queue', on_message_callback=callback_failed)

    channel.queue_declare(queue='shipping_failed_queue', durable=True)
    channel.basic_consume(queue='shipping_failed_queue', on_message_callback=callback_failed)

    print('Order service is waiting for Saga results...')
    channel.start_consuming()


if __name__ == "__main__":
    start_consuming()
