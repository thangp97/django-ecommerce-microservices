"""GraphRAG pipeline.

Bước 1: parse intent (keyword + price range + category gợi ý).
Bước 2: retrieve hybrid:
    - Vector/keyword search qua product name (TF-IDF đơn giản on-the-fly trên Neo4j).
    - Graph traversal: lịch sử user + similar users' purchases.
Bước 3: build context từ top-K.
Bước 4: generate answer — dùng Claude API nếu có ANTHROPIC_API_KEY, nếu không
         trả template Vietnamese.
"""
import os
import re
import json
import requests
from django.conf import settings

from .graph import get_driver


CATEGORY_HINTS = {
    'book': ['sách', 'book', 'đọc', 'tiểu thuyết', 'giáo trình'],
    'clothe': ['áo', 'quần', 'thời trang', 'đầm', 'váy'],
    'electronic': ['điện thoại', 'laptop', 'máy tính', 'tivi', 'điện tử', 'tai nghe'],
    'food': ['đồ ăn', 'thực phẩm', 'bánh', 'kẹo', 'sữa'],
    'toy': ['đồ chơi', 'con', 'em bé', 'trẻ em'],
    'furniture': ['bàn', 'ghế', 'tủ', 'giường', 'nội thất'],
    'cosmetic': ['mỹ phẩm', 'son', 'kem', 'dưỡng da'],
    'sport': ['thể thao', 'bóng', 'gym', 'tập luyện'],
    'stationery': ['văn phòng phẩm', 'bút', 'vở', 'giấy'],
    'appliance': ['máy giặt', 'tủ lạnh', 'gia dụng'],
    'jewelry': ['trang sức', 'nhẫn', 'dây chuyền', 'vàng', 'bạc'],
    'pet-supply': ['thú cưng', 'chó', 'mèo', 'cá cảnh'],
}

PRICE_PATTERN = re.compile(r'(\d+[\.,]?\d*)\s*(k|nghìn|ngàn|triệu|tr|m)?', re.IGNORECASE)


def parse_intent(message):
    msg = (message or '').lower()
    # Extract price range
    max_price = None
    if 'rẻ' in msg or 'giá thấp' in msg or 'giá rẻ' in msg:
        max_price = 500_000
    m = re.search(r'dưới\s*(\d+)\s*(k|nghìn|ngàn|triệu|tr|m)?', msg)
    if m:
        val = float(m.group(1))
        unit = (m.group(2) or '').lower()
        if unit in ('k', 'nghìn', 'ngàn'):
            val *= 1_000
        elif unit in ('triệu', 'tr', 'm'):
            val *= 1_000_000
        max_price = val
    # Detect category hints
    hinted_types = []
    for ptype, kws in CATEGORY_HINTS.items():
        if any(kw in msg for kw in kws):
            hinted_types.append(ptype)
    # Keywords còn lại (rough)
    tokens = re.findall(r'[\wÀ-ỹ]+', msg)
    stop = {'tôi', 'cần', 'muốn', 'mua', 'cho', 'là', 'gì', 'một', 'và', 'có', 'bạn',
            'nào', 'xin', 'chào', 'hãy', 'giúp', 'với', 'rẻ', 'thấp', 'dưới'}
    keywords = [t for t in tokens if len(t) > 1 and t not in stop]
    return {
        'max_price': max_price,
        'product_types': hinted_types,
        'keywords': keywords[:8],
    }


def _cypher_keyword_search(session, keywords, product_types, max_price, limit=10):
    if not keywords:
        keywords = ['']
    # Tìm sản phẩm có name chứa bất kỳ keyword nào
    where_parts = ["toLower(p.name) CONTAINS toLower($kw0)"]
    params = {'kw0': keywords[0], 'limit': limit}
    for i, kw in enumerate(keywords[1:], start=1):
        where_parts.append(f"toLower(p.name) CONTAINS toLower($kw{i})")
        params[f'kw{i}'] = kw
    where = '(' + ' OR '.join(where_parts) + ')'
    if product_types:
        where += ' AND p.type IN $ptypes'
        params['ptypes'] = product_types
    if max_price is not None:
        where += ' AND p.price <= $max_price'
        params['max_price'] = float(max_price)
    cypher = f"""
    MATCH (p:Product)
    WHERE {where}
    RETURN p.type AS type, p.id AS id, p.name AS name,
           p.price AS price, p.category AS category
    LIMIT $limit
    """
    return list(session.run(cypher, **params))


def _cypher_user_context(session, user_id, limit=5):
    """Lịch sử user + similar users' purchases."""
    if not user_id:
        return [], []
    history = list(session.run(
        """
        MATCH (u:User {id:$uid})-[r:PURCHASED|ADDED_TO_CART|VIEWED]->(p:Product)
        RETURN p.type AS type, p.id AS id, p.name AS name, p.price AS price,
               type(r) AS rel, coalesce(r.count,1) AS count
        ORDER BY count DESC LIMIT $limit
        """,
        uid=int(user_id), limit=limit,
    ))
    collaborative = list(session.run(
        """
        MATCH (u:User {id:$uid})-[:PURCHASED|ADDED_TO_CART]->(p)<-[:PURCHASED|ADDED_TO_CART]-(other:User)
        MATCH (other)-[r:PURCHASED|ADDED_TO_CART]->(rec:Product)
        WHERE other.id <> $uid AND NOT EXISTS {
            MATCH (u)-[:PURCHASED|ADDED_TO_CART|VIEWED]->(rec)
        }
        WITH rec, sum(coalesce(r.count,1)) AS score
        RETURN rec.type AS type, rec.id AS id, rec.name AS name,
               rec.price AS price, score
        ORDER BY score DESC LIMIT $limit
        """,
        uid=int(user_id), limit=limit,
    ))
    return history, collaborative


def retrieve(user_id, message):
    intent = parse_intent(message)
    with get_driver().session() as session:
        keyword_hits = _cypher_keyword_search(
            session, intent['keywords'], intent['product_types'], intent['max_price']
        )
        history, collab = _cypher_user_context(session, user_id)

    def _rec(row, source, score=0):
        return {
            'product_type': row['type'],
            'product_id': row['id'],
            'name': row['name'],
            'price': row['price'],
            'source': source,
            'score': score,
        }

    merged = {}
    for r in keyword_hits:
        key = (r['type'], r['id'])
        merged[key] = _rec(r, 'keyword', score=3)
    for r in collab:
        key = (r['type'], r['id'])
        if key in merged:
            merged[key]['score'] += 2
            merged[key]['source'] = 'hybrid'
        else:
            merged[key] = _rec(r, 'collaborative', score=2)

    recs = sorted(merged.values(), key=lambda x: -x['score'])[:8]
    return {
        'intent': intent,
        'recommendations': recs,
        'history': [_rec(h, 'history') for h in history],
    }


def _format_product(p):
    price = p.get('price') or 0
    return f"- {p['name']} ({p['product_type']}, {int(price):,}đ)"


def _template_answer(message, ctx):
    recs = ctx['recommendations']
    history = ctx['history']
    intent = ctx['intent']
    parts = []
    if not recs:
        return ("Xin lỗi, hiện tôi chưa tìm thấy sản phẩm phù hợp với yêu cầu của bạn. "
                "Bạn thử mô tả cụ thể hơn (loại sản phẩm, khoảng giá) nhé.")
    if intent['product_types']:
        parts.append(f"Dựa trên yêu cầu về {', '.join(intent['product_types'])}, tôi gợi ý:")
    else:
        parts.append("Tôi gợi ý một số sản phẩm phù hợp:")
    parts.extend(_format_product(r) for r in recs[:5])
    if history:
        parts.append("\nDựa trên lịch sử của bạn với: " +
                     ', '.join(h['name'] for h in history[:3]))
    if intent['max_price']:
        parts.append(f"\n(Đã lọc theo mức giá dưới {int(intent['max_price']):,}đ)")
    return '\n'.join(parts)


def _llm_answer(message, ctx):
    """Gọi Claude API nếu có ANTHROPIC_API_KEY, không thì trả template."""
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        return _template_answer(message, ctx)
    recs_text = '\n'.join(
        f"- {r['name']} (loại: {r['product_type']}, giá: {int(r.get('price',0)):,}đ)"
        for r in ctx['recommendations'][:6]
    )
    hist_text = '\n'.join(
        f"- {h['name']}" for h in ctx['history'][:3]
    ) or '(chưa có)'
    prompt = f"""Bạn là trợ lý mua sắm. Trả lời ngắn gọn bằng tiếng Việt (2-4 câu),
tự nhiên và thân thiện. Dựa trên ngữ cảnh sau:

[Câu hỏi của khách]
{message}

[Sản phẩm gợi ý từ graph database]
{recs_text or '(không có)'}

[Lịch sử mua sắm của khách]
{hist_text}

Hãy đưa ra câu trả lời và gợi ý 2-3 sản phẩm phù hợp nhất từ danh sách."""
    try:
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 400,
                'messages': [{'role': 'user', 'content': prompt}],
            },
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            return data['content'][0]['text']
    except Exception as e:
        print(f'[rag] claude error: {e}')
    return _template_answer(message, ctx)


def chat(user_id, message):
    ctx = retrieve(user_id, message)
    answer = _llm_answer(message, ctx)
    return {
        'answer': answer,
        'recommended_products': ctx['recommendations'][:6],
        'intent': ctx['intent'],
    }
