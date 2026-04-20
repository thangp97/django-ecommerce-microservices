"""Publish user-behavior events tới RabbitMQ exchange `user_behavior`.

Không throw nếu RabbitMQ down — event là best-effort, không block request.
"""
import json
import os
import threading
import pika


RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
EXCHANGE = os.environ.get('BEHAVIOR_EXCHANGE', 'user_behavior')

_lock = threading.Lock()
_conn = None
_channel = None


def _ensure_channel():
    global _conn, _channel
    if _channel is not None and not _channel.is_closed:
        return _channel
    _conn = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=30)
    )
    _channel = _conn.channel()
    _channel.exchange_declare(exchange=EXCHANGE, exchange_type='topic', durable=True)
    return _channel


def publish_event(event_type, user_id, product_type=None, product_id=None,
                  query=None, weight=1, routing_key=None):
    if user_id is None:
        return
    payload = {
        'event_type': event_type,
        'user_id': int(user_id),
        'product_type': product_type,
        'product_id': int(product_id) if product_id is not None else None,
        'query': query,
        'weight': weight,
    }
    rk = routing_key or (
        f'{event_type}.{product_type}' if product_type else event_type
    )
    try:
        with _lock:
            ch = _ensure_channel()
            ch.basic_publish(
                exchange=EXCHANGE,
                routing_key=rk,
                body=json.dumps(payload).encode('utf-8'),
                properties=pika.BasicProperties(delivery_mode=2),
            )
    except Exception as e:
        # Best effort — không làm gián đoạn request chính
        print(f'[behavior] publish failed: {e}')
        global _conn, _channel
        try:
            if _conn is not None:
                _conn.close()
        except Exception:
            pass
        _conn = None
        _channel = None
