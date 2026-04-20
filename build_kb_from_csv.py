"""Xay Knowledge-Base Graph (Neo4j) tu data_user500.csv.

Nodes  : User, Product, Category
Edges  : (User)-[:VIEWED {count}]->(Product)       # view + click
         (User)-[:ADDED_TO_CART {count}]->(Product)
         (Product)-[:BELONGS_TO]->(Category)

Quy tac weight:
         view        -> VIEWED +1
         click       -> VIEWED +2    (click the hien muc do engagement cao hon)
         add_to_cart -> ADDED_TO_CART +1
"""
import csv
import os
import sys
from collections import defaultdict

from neo4j import GraphDatabase

CSV_FILE = 'data_user500.csv'
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'bookstore123')


# ---------- 1. Aggregate CSV ----------
def aggregate(csv_file):
    """Tra ve 2 dict:
       edges[(uid, ptype, pid, rel)] = count
       products: set((ptype, pid))
       users   : set(uid)
    """
    edges = defaultdict(int)
    products, users = set(), set()
    with open(csv_file, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            uid = int(row['user_id'])
            pid = int(row['product_id'])
            ptype = row['product_type']
            action = row['action']
            users.add(uid)
            products.add((ptype, pid))
            if action == 'view':
                edges[(uid, ptype, pid, 'VIEWED')] += 1
            elif action == 'click':
                edges[(uid, ptype, pid, 'VIEWED')] += 2
            elif action == 'add_to_cart':
                edges[(uid, ptype, pid, 'ADDED_TO_CART')] += 1
    return edges, products, users


# ---------- 2. Write to Neo4j ----------
CYPHER_INIT = [
    "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
    "CREATE CONSTRAINT product_key IF NOT EXISTS FOR (p:Product) REQUIRE (p.type, p.id) IS UNIQUE",
    "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
]


def ingest(driver, edges, products, users):
    with driver.session() as s:
        # init schema
        for stmt in CYPHER_INIT:
            s.run(stmt)

        # users
        s.run(
            """
            UNWIND $uids AS uid
            MERGE (u:User {id:uid})
            """,
            uids=list(users),
        )
        print(f'  users  merged: {len(users)}')

        # products + categories
        plist = [{'ptype': t, 'pid': p} for (t, p) in products]
        s.run(
            """
            UNWIND $ps AS row
            MERGE (p:Product {type:row.ptype, id:row.pid})
            MERGE (c:Category {name:row.ptype})
            MERGE (p)-[:BELONGS_TO]->(c)
            """,
            ps=plist,
        )
        print(f'  products merged: {len(plist)} (+ {len({t for t, _ in products})} categories)')

        # edges — chia theo rel type (Cypher khong cho param hoa rel name)
        viewed = [
            {'uid': u, 'ptype': t, 'pid': p, 'w': w}
            for (u, t, p, r), w in edges.items() if r == 'VIEWED'
        ]
        added = [
            {'uid': u, 'ptype': t, 'pid': p, 'w': w}
            for (u, t, p, r), w in edges.items() if r == 'ADDED_TO_CART'
        ]

        s.run(
            """
            UNWIND $rows AS row
            MATCH (u:User {id:row.uid})
            MATCH (p:Product {type:row.ptype, id:row.pid})
            MERGE (u)-[r:VIEWED]->(p)
            ON CREATE SET r.count = row.w, r.last_at = datetime()
            ON MATCH  SET r.count = coalesce(r.count,0) + row.w, r.last_at = datetime()
            """,
            rows=viewed,
        )
        s.run(
            """
            UNWIND $rows AS row
            MATCH (u:User {id:row.uid})
            MATCH (p:Product {type:row.ptype, id:row.pid})
            MERGE (u)-[r:ADDED_TO_CART]->(p)
            ON CREATE SET r.count = row.w, r.last_at = datetime()
            ON MATCH  SET r.count = coalesce(r.count,0) + row.w, r.last_at = datetime()
            """,
            rows=added,
        )
        print(f'  edges VIEWED       : {len(viewed)}')
        print(f'  edges ADDED_TO_CART: {len(added)}')


# ---------- 3. Verify ----------
def verify(driver):
    with driver.session() as s:
        stats = {}
        stats['users']      = s.run('MATCH (u:User) RETURN count(u) AS c').single()['c']
        stats['products']   = s.run('MATCH (p:Product) RETURN count(p) AS c').single()['c']
        stats['categories'] = s.run('MATCH (c:Category) RETURN count(c) AS c').single()['c']
        stats['viewed']     = s.run('MATCH ()-[r:VIEWED]->() RETURN count(r) AS c').single()['c']
        stats['added']      = s.run('MATCH ()-[r:ADDED_TO_CART]->() RETURN count(r) AS c').single()['c']
        # top 5 product theo so user view
        top = s.run(
            """
            MATCH (p:Product)<-[r:VIEWED|ADDED_TO_CART]-(:User)
            WITH p, sum(coalesce(r.count,1)) AS score
            RETURN p.type AS type, p.id AS id, score
            ORDER BY score DESC LIMIT 5
            """
        ).data()
    print('\n=== Graph stats ===')
    for k, v in stats.items():
        print(f'  {k:<11}: {v}')
    print('\n=== Top 5 products theo engagement ===')
    for row in top:
        print(f'  {row["type"]:<12} id={row["id"]:<4} score={row["score"]}')


def main():
    print(f'=== Read {CSV_FILE} ===')
    edges, products, users = aggregate(CSV_FILE)
    print(f'  rows    : users={len(users)}  products={len(products)}  edges={len(edges)}')

    print(f'\n=== Connect {NEO4J_URI} ===')
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as s:
            s.run('RETURN 1').single()
        print('  [OK] connected')
    except Exception as e:
        print(f'  [FATAL] khong ket noi duoc Neo4j: {e}')
        sys.exit(1)

    print('\n=== Ingest ===')
    ingest(driver, edges, products, users)

    verify(driver)
    driver.close()
    print('\n[DONE] KB_Graph built.')


if __name__ == '__main__':
    main()
