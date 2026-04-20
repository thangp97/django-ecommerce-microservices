"""Sinh data_user500.csv: 500 user x 20 behaviors voi pattern realistic.

Pattern sinh (khac hoan toan voi bang random truoc day):
  1. THEME per user: moi user co 1 primary theme (70% hanh vi) + 1 secondary (15%)
     + related-category (10%) + random noise (5%).
  2. MARKOV action: view -> click -> add_to_cart co xu huong noi tiep
     (realistic: xem -> thich -> bo gio).
  3. FAVORITE products: trong theme chinh, user co 2-3 product "yeu thich"
     duoc chon nhieu hon.
  4. CHRONOLOGICAL timestamp: cac hanh vi noi tiep nhau trong 3 tuan,
     gap 1-24h giua 2 hanh vi.

Cot CSV: user_id, product_id, product_type, action, timestamp
"""
import csv
import random
import sys
from datetime import datetime, timedelta, timezone

import requests

SERVICES = [
    (8002, 'books',        'book'),
    (8013, 'clothes',      'clothe'),
    (8020, 'electronics',  'electronic'),
    (8021, 'foods',        'food'),
    (8022, 'toys',         'toy'),
    (8023, 'furnitures',   'furniture'),
    (8024, 'cosmetics',    'cosmetic'),
    (8025, 'sports',       'sport'),
    (8026, 'stationeries', 'stationery'),
    (8027, 'appliances',   'appliance'),
    (8028, 'jewelries',    'jewelry'),
    (8029, 'pet-supplies', 'pet-supply'),
]

# Category thuong di cung nhau (realistic co-occurrence)
RELATED = {
    'book':        ['stationery', 'toy'],
    'clothe':      ['cosmetic', 'sport', 'jewelry'],
    'electronic':  ['appliance', 'stationery'],
    'food':        ['appliance', 'pet-supply'],
    'toy':         ['book'],
    'furniture':   ['appliance'],
    'cosmetic':    ['jewelry', 'clothe'],
    'sport':       ['clothe'],
    'stationery':  ['book', 'electronic'],
    'appliance':   ['electronic', 'food', 'furniture'],
    'jewelry':     ['cosmetic', 'clothe'],
    'pet-supply':  ['food'],
}
ALL_TYPES = list(RELATED.keys())

# Markov cho action: P(next | prev)
ACTION_TRANS = {
    None:          [('view', 0.90), ('click', 0.10), ('add_to_cart', 0.00)],
    'view':        [('view', 0.50), ('click', 0.40), ('add_to_cart', 0.10)],
    'click':       [('view', 0.30), ('click', 0.30), ('add_to_cart', 0.40)],
    'add_to_cart': [('view', 0.60), ('click', 0.30), ('add_to_cart', 0.10)],
}

N_USERS = 500
BEHAVIORS_PER_USER = 20
OUT_FILE = 'data_user500.csv'


def weighted_choice(pairs):
    vals, weights = zip(*pairs)
    return random.choices(vals, weights=weights, k=1)[0]


def fetch_products():
    """Lay products group theo type -> dict[ptype] = [pid,...]"""
    items = {}
    for port, plural, ptype in SERVICES:
        try:
            r = requests.get(f'http://localhost:{port}/{plural}/', timeout=5)
            if r.status_code != 200:
                print(f'  [WARN] {ptype}: http {r.status_code}')
                continue
            data = r.json()
            ids = [int(p['id']) for p in data if p.get('id') is not None]
            if ids:
                items[ptype] = ids
                print(f'  [OK]  {ptype:<12} {len(ids)} products')
        except Exception as e:
            print(f'  [ERR] {ptype}: {e}')
    return items


def sample_next_type(cur_type, primary, secondary):
    """
    70%: primary theme
    15%: secondary theme
    10%: related to cur_type
     5%: random
    """
    r = random.random()
    if r < 0.70:
        return primary
    if r < 0.85:
        return secondary
    if r < 0.95:
        rels = RELATED.get(cur_type, [])
        return random.choice(rels) if rels else primary
    return random.choice(ALL_TYPES)


def sample_next_action(prev):
    return weighted_choice(ACTION_TRANS[prev])


def main():
    random.seed(42)
    print('=== Fetching products ===')
    products = fetch_products()
    if not products:
        print('[FATAL] khong lay duoc product nao')
        sys.exit(1)
    valid_types = [t for t in ALL_TYPES if products.get(t)]
    print(f'=> {sum(len(v) for v in products.values())} products in {len(valid_types)} types\n')

    print(f'=== Generating {N_USERS} users x {BEHAVIORS_PER_USER} behaviors ===')
    now = datetime.now(timezone.utc)
    rows = []

    for uid in range(1, N_USERS + 1):
        # 1. Pick themes
        primary = random.choice(valid_types)
        secondary = random.choice([t for t in valid_types if t != primary])
        # 2. Favorites trong primary theme
        primary_pool = products[primary]
        favorites = random.sample(primary_pool, k=min(3, len(primary_pool)))

        # 3. Walk
        cur_type = primary
        cur_action = None
        cur_time = now - timedelta(days=random.randint(15, 29))

        for _ in range(BEHAVIORS_PER_USER):
            cur_type = sample_next_type(cur_type, primary, secondary)
            pool = products.get(cur_type) or primary_pool
            # Bias ve favorite neu dang o primary theme
            if cur_type == primary and random.random() < 0.6:
                pid = random.choice(favorites)
            else:
                pid = random.choice(pool)
            cur_action = sample_next_action(cur_action)
            cur_time += timedelta(
                hours=random.randint(1, 24),
                minutes=random.randint(0, 59),
            )
            rows.append((uid, pid, cur_type, cur_action, cur_time.isoformat()))

    with open(OUT_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['user_id', 'product_id', 'product_type', 'action', 'timestamp'])
        w.writerows(rows)

    # Stats
    action_stats = {}
    type_stats = {}
    for r in rows:
        action_stats[r[3]] = action_stats.get(r[3], 0) + 1
        type_stats[r[2]] = type_stats.get(r[2], 0) + 1
    print(f'\n[OK] wrote {len(rows)} rows -> {OUT_FILE}')
    print('Action distribution:', action_stats)
    print('Type distribution :', sorted(type_stats.items(), key=lambda x: -x[1])[:5], '...')


if __name__ == '__main__':
    main()
