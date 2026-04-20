"""Ingest worker: subscribe RabbitMQ exchange `user_behavior`, ghi Neo4j."""
import os
import sys
import json
import time
import django

sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_service.settings')
django.setup()

import pika  # noqa: E402
from django.conf import settings  # noqa: E402
from app.graph import get_driver, init_schema, record_event  # noqa: E402


EXCHANGE = settings.BEHAVIOR_EXCHANGE
QUEUE = 'ai_ingest_queue'


def handle(ch, method, properties, body):
    try:
        event = json.loads(body)
    except Exception as e:
        print(f'[ingest] invalid json: {e}')
        ch.basic_ack(method.delivery_tag)
        return

    user_id = event.get('user_id')
    etype = event.get('event_type')
    ptype = event.get('product_type')
    pid = event.get('product_id')
    query = event.get('query')
    weight = event.get('weight', 1)

    if not user_id or not etype:
        ch.basic_ack(method.delivery_tag)
        return

    try:
        with get_driver().session() as s:
            s.execute_write(record_event, user_id, etype, ptype, pid, query, weight)
        print(f'[ingest] {etype} user={user_id} {ptype}:{pid} q={query!r}')
    except Exception as e:
        print(f'[ingest] neo4j error: {e}')
    ch.basic_ack(method.delivery_tag)


def connect_with_retry(retries=30, delay=2):
    for i in range(retries):
        try:
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(host=settings.RABBITMQ_HOST, heartbeat=60)
            )
            return conn
        except Exception as e:
            print(f'[ingest] rabbitmq not ready ({i+1}/{retries}): {e}')
            time.sleep(delay)
    raise RuntimeError('rabbitmq unavailable')


def init_neo4j_with_retry(retries=30, delay=2):
    for i in range(retries):
        try:
            init_schema()
            print('[ingest] neo4j schema initialized')
            return
        except Exception as e:
            print(f'[ingest] neo4j not ready ({i+1}/{retries}): {e}')
            time.sleep(delay)
    raise RuntimeError('neo4j unavailable')


def main():
    init_neo4j_with_retry()
    conn = connect_with_retry()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type='topic', durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key='#')
    ch.basic_qos(prefetch_count=32)
    ch.basic_consume(queue=QUEUE, on_message_callback=handle)
    print(f'[ingest] consuming from {EXCHANGE}...')
    ch.start_consuming()


if __name__ == '__main__':
    main()
