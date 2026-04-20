"""AI service HTTP endpoints."""
import json
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from .graph import get_driver, init_schema, upsert_product
from .rag import chat as rag_chat


@api_view(['GET'])
def health(request):
    ok = True
    msg = 'ok'
    try:
        with get_driver().session() as s:
            s.run('RETURN 1').single()
    except Exception as e:
        ok = False
        msg = f'neo4j: {e}'
    return JsonResponse({'status': 'ok' if ok else 'error', 'detail': msg})


@csrf_exempt
@api_view(['POST'])
def bootstrap(request):
    """Crawl toàn bộ product từ 12 service và nạp vào Neo4j."""
    init_schema()
    total = 0
    per_type = {}
    with get_driver().session() as session:
        for ptype, (base_url, plural) in settings.PRODUCT_SERVICE_MAP.items():
            try:
                r = requests.get(f'{base_url}/{plural}/', timeout=5)
                if r.status_code != 200:
                    per_type[ptype] = f'http {r.status_code}'
                    continue
                items = r.json()
                if not isinstance(items, list):
                    per_type[ptype] = 'not list'
                    continue
                count = 0
                for p in items:
                    pid = p.get('id')
                    name = p.get('title') or p.get('name') or ''
                    price = p.get('price', 0)
                    category = p.get('category') or p.get('genre') or ptype
                    if pid is None:
                        continue
                    session.execute_write(
                        upsert_product, ptype, int(pid), name, price, category
                    )
                    count += 1
                per_type[ptype] = count
                total += count
            except Exception as e:
                per_type[ptype] = f'error: {e}'
    return JsonResponse({'total': total, 'per_type': per_type})


@api_view(['GET'])
def recommend(request):
    """Co-occurrence recommender dựa trên graph.

    Logic: tìm users đã mua cùng sản phẩm với user hiện tại → gợi ý sản phẩm
    họ đã mua mà user hiện tại chưa tương tác.
    """
    try:
        user_id = int(request.GET.get('user_id', '0'))
    except ValueError:
        return JsonResponse({'error': 'invalid user_id'}, status=400)
    try:
        limit = max(1, min(int(request.GET.get('limit', '10')), 50))
    except ValueError:
        limit = 10

    cypher = """
    MATCH (u:User {id:$uid})-[:PURCHASED|ADDED_TO_CART|VIEWED]->(p:Product)
    WITH u, collect(DISTINCT p) AS seen
    UNWIND seen AS sp
    MATCH (sp)<-[:PURCHASED|ADDED_TO_CART]-(other:User)-[r:PURCHASED|ADDED_TO_CART]->(rec:Product)
    WHERE other.id <> $uid AND NOT rec IN seen
    WITH rec, sum(coalesce(r.count,1)) AS score
    RETURN rec.type AS product_type, rec.id AS product_id,
           rec.name AS name, rec.price AS price, score
    ORDER BY score DESC
    LIMIT $limit
    """
    results = []
    try:
        with get_driver().session() as s:
            res = s.run(cypher, uid=user_id, limit=limit)
            for rec in res:
                results.append({
                    'product_type': rec['product_type'],
                    'product_id': rec['product_id'],
                    'name': rec['name'],
                    'price': rec['price'],
                    'score': rec['score'],
                })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    # Fallback: popular products nếu user chưa có history
    if not results:
        cypher_pop = """
        MATCH (p:Product)<-[r:PURCHASED|ADDED_TO_CART|VIEWED]-(:User)
        WITH p, sum(coalesce(r.count,1)) AS score
        RETURN p.type AS product_type, p.id AS product_id,
               p.name AS name, p.price AS price, score
        ORDER BY score DESC
        LIMIT $limit
        """
        try:
            with get_driver().session() as s:
                res = s.run(cypher_pop, limit=limit)
                for rec in res:
                    results.append({
                        'product_type': rec['product_type'],
                        'product_id': rec['product_id'],
                        'name': rec['name'],
                        'price': rec['price'],
                        'score': rec['score'],
                        'fallback': 'popular',
                    })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'user_id': user_id, 'recommendations': results})


@api_view(['GET'])
def similar(request):
    """Sản phẩm tương tự dựa trên co-view/co-purchase."""
    ptype = request.GET.get('product_type')
    try:
        pid = int(request.GET.get('product_id', '0'))
    except ValueError:
        return JsonResponse({'error': 'invalid product_id'}, status=400)
    try:
        limit = max(1, min(int(request.GET.get('limit', '8')), 30))
    except ValueError:
        limit = 8
    if not ptype or not pid:
        return JsonResponse({'error': 'missing product_type/product_id'}, status=400)

    cypher = """
    MATCH (p:Product {type:$ptype, id:$pid})<-[:PURCHASED|VIEWED|ADDED_TO_CART]-(u:User)
          -[r:PURCHASED|VIEWED|ADDED_TO_CART]->(other:Product)
    WHERE other <> p
    WITH other, sum(coalesce(r.count,1)) AS score
    RETURN other.type AS product_type, other.id AS product_id,
           other.name AS name, other.price AS price, score
    ORDER BY score DESC
    LIMIT $limit
    """
    results = []
    try:
        with get_driver().session() as s:
            res = s.run(cypher, ptype=ptype, pid=pid, limit=limit)
            for rec in res:
                results.append({
                    'product_type': rec['product_type'],
                    'product_id': rec['product_id'],
                    'name': rec['name'],
                    'price': rec['price'],
                    'score': rec['score'],
                })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'product_type': ptype, 'product_id': pid, 'similar': results})


@csrf_exempt
@api_view(['POST'])
def chat(request):
    """GraphRAG chat. Body: {user_id, message}."""
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
        user_id = data.get('user_id')
        message = (data.get('message') or '').strip()
    except Exception as e:
        return JsonResponse({'error': f'invalid body: {e}'}, status=400)
    if not message:
        return JsonResponse({'error': 'missing message'}, status=400)
    try:
        result = rag_chat(user_id, message)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
def graph_stats(request):
    """Thống kê nhanh cho demo."""
    stats = {}
    try:
        with get_driver().session() as s:
            stats['users'] = s.run('MATCH (u:User) RETURN count(u) AS c').single()['c']
            stats['products'] = s.run('MATCH (p:Product) RETURN count(p) AS c').single()['c']
            stats['categories'] = s.run('MATCH (c:Category) RETURN count(c) AS c').single()['c']
            stats['queries'] = s.run('MATCH (q:Query) RETURN count(q) AS c').single()['c']
            stats['edges'] = s.run('MATCH ()-[r]->() RETURN count(r) AS c').single()['c']
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse(stats)
