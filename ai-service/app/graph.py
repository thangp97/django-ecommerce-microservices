"""Neo4j driver wrapper + schema helpers."""
from neo4j import GraphDatabase
from django.conf import settings

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def init_schema():
    """Tạo constraints + index. Idempotent."""
    cypher = [
        "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
        "CREATE CONSTRAINT product_key IF NOT EXISTS FOR (p:Product) REQUIRE (p.type, p.id) IS UNIQUE",
        "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT query_text IF NOT EXISTS FOR (q:Query) REQUIRE q.text IS UNIQUE",
    ]
    with get_driver().session() as s:
        for stmt in cypher:
            s.run(stmt)


# ─── Write helpers ───────────────────────────────────────────

def upsert_product(tx, ptype, pid, name, price, category):
    tx.run(
        """
        MERGE (p:Product {type:$ptype, id:$pid})
        SET p.name=$name, p.price=$price, p.category=$category
        WITH p
        FOREACH (_ IN CASE WHEN $category IS NULL OR $category = '' THEN [] ELSE [1] END |
            MERGE (c:Category {name:$category})
            MERGE (p)-[:BELONGS_TO]->(c)
        )
        """,
        ptype=ptype, pid=pid, name=name or '', price=float(price or 0), category=category or '',
    )


def record_event(tx, user_id, event_type, ptype=None, pid=None, query=None, weight=1):
    """event_type: view | add_to_cart | remove_from_cart | purchase | search"""
    tx.run("MERGE (u:User {id:$uid})", uid=int(user_id))
    if event_type == 'search' and query:
        tx.run(
            """
            MERGE (q:Query {text:$qtext})
            WITH q
            MATCH (u:User {id:$uid})
            MERGE (u)-[r:SEARCHED]->(q)
            ON CREATE SET r.count=1, r.last_at=datetime()
            ON MATCH SET r.count=coalesce(r.count,0)+1, r.last_at=datetime()
            """,
            uid=int(user_id), qtext=query,
        )
        return
    if ptype is None or pid is None:
        return
    rel_map = {
        'view': 'VIEWED',
        'add_to_cart': 'ADDED_TO_CART',
        'remove_from_cart': 'REMOVED_FROM_CART',
        'purchase': 'PURCHASED',
    }
    rel = rel_map.get(event_type)
    if not rel:
        return
    tx.run(
        f"""
        MATCH (u:User {{id:$uid}})
        MERGE (p:Product {{type:$ptype, id:$pid}})
        MERGE (u)-[r:{rel}]->(p)
        ON CREATE SET r.count=$w, r.last_at=datetime()
        ON MATCH SET r.count=coalesce(r.count,0)+$w, r.last_at=datetime()
        """,
        uid=int(user_id), ptype=ptype, pid=int(pid), w=int(weight),
    )
