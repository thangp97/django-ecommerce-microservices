"""
Script seed data for AI system testing.
Run: python seed_data.py
Requires: docker compose up
"""

import sys
import io
# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import time

BASE = {
    "book":     "http://localhost:8002",
    "clothe":   "http://localhost:8013",
    "customer": "http://localhost:8001",
    "order":    "http://localhost:8004",
    "review":   "http://localhost:8010",
    "ai":       "http://localhost:8011",
}

# ─────────────────────────────────────────────────
# Màu terminal để dễ đọc
# ─────────────────────────────────────────────────
def ok(msg):      print(f"  [OK]   {msg}")
def warn(msg):    print(f"  [WARN] {msg}")
def err(msg):     print(f"  [ERR]  {msg}")
def info(msg):    print(f"  [-->]  {msg}")
def section(msg): print(f"\n{'='*55}\n  {msg}\n{'='*55}")

def post(url, data):
    try:
        resp = requests.post(url, json=data, timeout=10)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"error": str(e)}, 0

def get(url):
    try:
        resp = requests.get(url, timeout=10)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"error": str(e)}, 0


# ─────────────────────────────────────────────────
# BƯỚC 0: Kiểm tra services có đang chạy không
# ─────────────────────────────────────────────────
def check_services():
    section("Kiểm tra kết nối services")
    all_ok = True
    for name, base in BASE.items():
        try:
            requests.get(base, timeout=3)
            ok(f"{name:10s} ({base})")
        except Exception:
            err(f"{name:10s} ({base}) — KHÔNG KẾT NỐI ĐƯỢC")
            all_ok = False
    if not all_ok:
        print(f"\n{RED}Một số service chưa chạy. Hãy chắc chắn docker compose up đã xong.{RESET}")
        sys.exit(1)


# ─────────────────────────────────────────────────
# BƯỚC 1: Tạo Sách
# ─────────────────────────────────────────────────
BOOKS = [
    # IT & Lập trình
    {
        "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
        "author": "Robert C. Martin",
        "price": "320000.00",
        "stock": 50,
        "description": "Sách kinh điển về viết code sạch, dễ đọc và bảo trì cho lập trình viên",
    },
    {
        "title": "Python Machine Learning",
        "author": "Sebastian Raschka",
        "price": "450000.00",
        "stock": 40,
        "description": "Học Machine Learning với Python từ cơ bản đến nâng cao, bao gồm Deep Learning",
    },
    {
        "title": "Designing Data-Intensive Applications",
        "author": "Martin Kleppmann",
        "price": "520000.00",
        "stock": 30,
        "description": "Xây dựng hệ thống dữ liệu lớn, đáng tin cậy và có khả năng mở rộng",
    },
    {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt & David Thomas",
        "price": "290000.00",
        "stock": 45,
        "description": "Bí quyết để trở thành lập trình viên chuyên nghiệp và hiệu quả",
    },
    # Y học & Sức khỏe
    {
        "title": "Gray's Anatomy for Students",
        "author": "Richard Drake",
        "price": "680000.00",
        "stock": 20,
        "description": "Giải phẫu học toàn diện dành cho sinh viên y khoa với hình ảnh chi tiết",
    },
    {
        "title": "Harrison's Principles of Internal Medicine",
        "author": "J. Larry Jameson",
        "price": "850000.00",
        "stock": 15,
        "description": "Tài liệu y học nội khoa kinh điển dành cho bác sĩ và sinh viên y",
    },
    # Kinh doanh & Phát triển bản thân
    {
        "title": "Atomic Habits",
        "author": "James Clear",
        "price": "185000.00",
        "stock": 100,
        "description": "Xây dựng thói quen tốt và loại bỏ thói quen xấu bằng những thay đổi nhỏ mỗi ngày",
    },
    {
        "title": "The Lean Startup",
        "author": "Eric Ries",
        "price": "210000.00",
        "stock": 60,
        "description": "Phương pháp khởi nghiệp tinh gọn giúp xây dựng sản phẩm hiệu quả và giảm rủi ro",
    },
    # Văn học & Giáo dục
    {
        "title": "Sapiens: A Brief History of Humankind",
        "author": "Yuval Noah Harari",
        "price": "245000.00",
        "stock": 80,
        "description": "Lịch sử ngắn gọn về loài người từ thời kỳ đồ đá đến thế kỷ 21",
    },
    {
        "title": "The Art of Learning",
        "author": "Josh Waitzkin",
        "price": "195000.00",
        "stock": 55,
        "description": "Phương pháp học tập hiệu quả và phát triển kỹ năng đỉnh cao",
    },
]

# ─────────────────────────────────────────────────
# BƯỚC 2: Tạo Quần áo
# ─────────────────────────────────────────────────
CLOTHES = [
    {
        "name": "Áo thun basic cotton unisex",
        "material": "100% Cotton",
        "price": "150000.00",
        "stock": 200,
    },
    {
        "name": "Quần jeans slim fit nam",
        "material": "Denim 98% Cotton 2% Elastane",
        "price": "450000.00",
        "stock": 80,
    },
    {
        "name": "Áo sơ mi trắng công sở nữ",
        "material": "Polyester 65% Cotton 35%",
        "price": "280000.00",
        "stock": 120,
    },
    {
        "name": "Hoodie nỉ bông form oversize",
        "material": "Nỉ bông 80% Cotton 20% Polyester",
        "price": "380000.00",
        "stock": 90,
    },
    {
        "name": "Váy midi hoa nhí dáng xòe",
        "material": "Vải hoa nhí lụa tơ tằm",
        "price": "320000.00",
        "stock": 60,
    },
]

# ─────────────────────────────────────────────────
# BƯỚC 3: Tạo Khách hàng (đa dạng ngành nghề để test NCF)
# ─────────────────────────────────────────────────
CUSTOMERS = [
    # customer 1: Kỹ sư IT → nên thích sách IT
    {
        "name": "Nguyễn Văn An",
        "email": "an.nguyen@gmail.com",
        "password": "password123",
        "job_title": "Software Engineer",   # chỉ dùng để ghi chú, không POST trực tiếp
        "preferred_books": [0, 1, 2, 3],    # index trong BOOKS
        "preferred_clothes": [0, 3],
    },
    # customer 2: Bác sĩ → nên thích sách y học
    {
        "name": "Trần Thị Bình",
        "email": "binh.tran@gmail.com",
        "password": "password123",
        "job_title": "Doctor",
        "preferred_books": [4, 5, 8],
        "preferred_clothes": [2, 4],
    },
    # customer 3: Sinh viên → đọc đa dạng
    {
        "name": "Lê Minh Cường",
        "email": "cuong.le@gmail.com",
        "password": "password123",
        "job_title": "Student",
        "preferred_books": [6, 7, 9, 1],
        "preferred_clothes": [0, 1],
    },
    # customer 4: Chủ doanh nghiệp → sách kinh doanh
    {
        "name": "Phạm Thu Dung",
        "email": "dung.pham@gmail.com",
        "password": "password123",
        "job_title": "Business Owner",
        "preferred_books": [6, 7, 8],
        "preferred_clothes": [2, 3],
    },
    # customer 5: Kỹ sư IT khác → confirm pattern cho NCF
    {
        "name": "Hoàng Văn Em",
        "email": "em.hoang@gmail.com",
        "password": "password123",
        "job_title": "Software Engineer",
        "preferred_books": [0, 2, 1, 3],
        "preferred_clothes": [3, 0],
    },
]


def seed_books():
    section("1. Tạo Sách (10 cuốn)")
    created_books = []
    for book in BOOKS:
        payload = {k: v for k, v in book.items() if k != "description"}
        # Thêm description nếu model có field này
        data, status = post(f"{BASE['book']}/books/", payload)
        if status in (200, 201):
            ok(f"[Book #{data.get('id')}] {book['title'][:50]}")
            created_books.append(data)
        elif "id" in str(data):
            ok(f"Đã tồn tại: {book['title'][:50]}")
        else:
            warn(f"Lỗi tạo sách '{book['title'][:40]}': {data}")
    return created_books


def seed_clothes():
    section("2. Tạo Quần áo (5 sản phẩm)")
    created_clothes = []
    for clothe in CLOTHES:
        data, status = post(f"{BASE['clothe']}/clothes/", clothe)
        if status in (200, 201):
            ok(f"[Clothe #{data.get('id')}] {clothe['name']}")
            created_clothes.append(data)
        else:
            warn(f"Lỗi tạo quần áo '{clothe['name']}': {data}")
    return created_clothes


def get_jobs():
    """Lấy danh sách jobs (trigger auto-create default jobs)."""
    data, status = get(f"{BASE['customer']}/jobs/")
    if status == 200 and isinstance(data, list):
        return {job['title']: job['id'] for job in data}
    return {}


def seed_customers(jobs_map):
    section("3. Tạo Khách hàng (5 người)")
    created_customers = []
    for cust in CUSTOMERS:
        payload = {
            "name": cust["name"],
            "email": cust["email"],
            "password": cust["password"],
        }
        # Gán job nếu có
        job_id = jobs_map.get(cust["job_title"])
        if job_id:
            payload["job"] = job_id

        data, status = post(f"{BASE['customer']}/customers/", payload)
        if status in (200, 201):
            ok(f"[Customer #{data.get('id')}] {cust['name']} ({cust['job_title']})")
            created_customers.append(data)
        else:
            warn(f"Lỗi hoặc đã tồn tại '{cust['name']}': {data}")
    return created_customers


def seed_orders(customers, books):
    """
    Tạo đơn hàng dựa trên sở thích của từng customer.
    Mỗi customer mua các sách trong 'preferred_books'.
    """
    section("4. Tạo Đơn hàng")

    if not customers or not books:
        err("Không có customers hoặc books để tạo orders")
        return []

    created_orders = []

    for i, cust_data in enumerate(customers):
        if i >= len(CUSTOMERS):
            break

        cust_id = cust_data.get("id")
        if not cust_id:
            continue

        cust_config = CUSTOMERS[i]
        preferred_indices = cust_config.get("preferred_books", [0, 1])

        # Lấy 2-3 sách preferred để tạo đơn hàng
        order_book_indices = preferred_indices[:3]
        order_books = [books[idx] for idx in order_book_indices if idx < len(books)]

        if not order_books:
            continue

        # Tính tổng giá
        items = []
        total = 0
        for book in order_books:
            price = float(book.get("price", 100000))
            items.append({
                "book_id": book["id"],
                "quantity": 1,
                "price": price,
            })
            total += price

        shipping_fee = 0 if total >= 300000 else 30000
        payload = {
            "customer_id": cust_id,
            "items": items,
            "total_price": total,
            "shipping_fee": shipping_fee,
            "shipping_address": f"123 Đường Mẫu, Quận {i+1}, TP.HCM",
            "payment_method": "cod",
        }

        data, status = post(f"{BASE['order']}/orders/", payload)
        if status in (200, 201):
            ok(f"[Order #{data.get('id')}] Customer #{cust_id} mua {len(items)} sách — {total:,.0f} VND")
            created_orders.append(data)
        else:
            warn(f"Lỗi tạo order cho customer #{cust_id}: {data}")

        time.sleep(0.3)  # Tránh quá tải RabbitMQ

    return created_orders


def seed_reviews(customers, books):
    """
    Tạo đánh giá: mỗi customer đánh giá các sách họ có xu hướng thích.
    Rating được gán dựa trên mức độ phù hợp với ngành nghề.
    """
    section("5. Tạo Đánh giá sách")

    if not customers or not books:
        err("Không có customers hoặc books để tạo reviews")
        return []

    # Rating matrix: [customer_index][book_index] = rating (1-5)
    # Thiết kế để NCF học được pattern rõ ràng:
    #   - IT engineer → sách IT rating cao
    #   - Doctor → sách y học rating cao
    #   - Student → đa dạng, rating trung bình
    ratings_config = [
        # Customer 0: Software Engineer
        {0: 5, 1: 5, 2: 4, 3: 4, 4: 2, 5: 1, 6: 3, 7: 3, 8: 3, 9: 4},
        # Customer 1: Doctor
        {0: 2, 1: 3, 2: 2, 3: 2, 4: 5, 5: 5, 6: 4, 7: 3, 8: 4, 9: 3},
        # Customer 2: Student
        {0: 3, 1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 5, 7: 4, 8: 5, 9: 5},
        # Customer 3: Business Owner
        {0: 3, 1: 3, 2: 3, 3: 3, 4: 2, 5: 2, 6: 5, 7: 5, 8: 4, 9: 3},
        # Customer 4: Software Engineer (tương tự customer 0)
        {0: 5, 1: 4, 2: 5, 3: 5, 4: 2, 5: 1, 6: 3, 7: 2, 8: 4, 9: 4},
    ]

    comments = {
        5: ["Tuyệt vời! Rất hữu ích cho công việc.", "Sách hay nhất tôi từng đọc.", "Recommend cho mọi người!"],
        4: ["Sách tốt, nhiều kiến thức bổ ích.", "Đáng đọc, sẽ mua lại lần sau.", "Nội dung chất lượng."],
        3: ["Sách bình thường, đọc được.", "Khá ổn cho người mới.", "Có một số phần thú vị."],
        2: ["Không như kỳ vọng.", "Nội dung hơi khô khan.", "Chỉ phù hợp với chuyên ngành."],
        1: ["Không phù hợp với tôi.", "Quá khó để theo dõi."],
    }

    import random
    created_reviews = []
    total_reviews = 0

    for i, cust_data in enumerate(customers):
        if i >= len(CUSTOMERS) or i >= len(ratings_config):
            break

        cust_id = cust_data.get("id")
        if not cust_id:
            continue

        ratings = ratings_config[i]

        for book_idx, rating in ratings.items():
            if book_idx >= len(books):
                continue

            book = books[book_idx]
            comment = random.choice(comments[rating])

            payload = {
                "customer_id": cust_id,
                "book_id": book["id"],
                "rating": rating,
                "comment": comment,
            }

            data, status = post(f"{BASE['review']}/reviews/", payload)
            if status in (200, 201):
                total_reviews += 1
            elif "unique" in str(data).lower() or "already" in str(data).lower():
                pass  # đã tồn tại, bỏ qua
            else:
                warn(f"Review lỗi customer#{cust_id} book#{book['id']}: {data}")

        ok(f"Customer #{cust_id} ({CUSTOMERS[i]['name']}) — đã tạo {len(ratings)} đánh giá")

    print(f"\n  Tổng đánh giá đã tạo: {total_reviews}")
    return created_reviews


def trigger_ai_setup():
    """Sau khi có data, tự động sync KB và train model."""
    section("6. Kích hoạt AI System")

    # Sync Knowledge Base
    info("Đồng bộ Knowledge Base (ChromaDB)...")
    data, status = post(f"{BASE['ai']}/ai/knowledge/sync/", {})
    if status == 200:
        ok(f"Knowledge Base synced: {data.get('synced_books', 0)} sách, {data.get('synced_clothes', 0)} quần áo")
        ok(f"Chính sách: {data.get('seeded_policies', 0)}, FAQ: {data.get('seeded_faqs', 0)}")
    else:
        warn(f"KB sync lỗi: {data}")

    # Train NCF model
    info("Train mô hình NCF Deep Learning...")
    data, status = post(f"{BASE['ai']}/ai/train/", {"epochs": 30})
    if status == 200:
        ok(f"Model trained! Loss: {data.get('final_loss', 'N/A'):.4f}")
        ok(f"Users: {data.get('num_users')}, Items: {data.get('num_items')}, Interactions: {data.get('num_interactions')}")
    else:
        warn(f"Train model lỗi: {data}")
        if "tip" in data:
            info(data["tip"])


def print_test_guide(customers, books):
    """Hướng dẫn test sau khi seed xong."""
    section("HƯỚNG DẪN TEST")

    if customers:
        cust_id = customers[0].get("id", 1)
        print(f"""
Test Goi y AI (NCF Deep Learning):
  GET http://localhost:8011/ai/recommend/{cust_id}/

Test RAG Chatbot:
  POST http://localhost:8011/ai/chat/
  Body: {{"message": "Chinh sach doi tra nhu the nao?"}}
  Body: {{"message": "Goi y sach cho ky su IT"}}
  Body: {{"message": "Co sach ve y hoc khong?"}}

Test Tim kiem ngu nghia:
  POST http://localhost:8011/ai/knowledge/search/
  Body: {{"query": "sach lap trinh python", "n_results": 3}}

Xem Dashboard AI:
  GET http://localhost:8011/ai/

Goi y Rule-based (cu):
  GET http://localhost:8011/recommendations/{cust_id}/

Thong ke Knowledge Base:
  GET http://localhost:8011/ai/knowledge/stats/
""")

    print("Danh sach Customers da tao:")
    for i, c in enumerate(customers):
        job = CUSTOMERS[i]["job_title"] if i < len(CUSTOMERS) else "Unknown"
        print(f"  #{c.get('id'):3d} | {c.get('name', ''):<20s} | {CUSTOMERS[i]['email']:<30s} | {job}")


# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{'='*55}")
    print("   SEED DATA CHO AI E-COMMERCE SYSTEM")
    print(f"{'='*55}")

    check_services()

    # 1. Tạo sản phẩm
    books   = seed_books()
    clothes = seed_clothes()

    # 2. Lấy jobs và tạo customers
    info("Lấy danh sách Job categories...")
    jobs_map = get_jobs()
    if jobs_map:
        ok(f"Tìm thấy {len(jobs_map)} loại job: {', '.join(list(jobs_map.keys())[:5])}")
    customers = seed_customers(jobs_map)

    # 3. Tạo orders và reviews
    if books and customers:
        seed_orders(customers, books)
        seed_reviews(customers, books)
    else:
        warn("Bỏ qua orders/reviews vì thiếu books hoặc customers")

    # 4. Trigger AI setup
    if books and customers:
        trigger_ai_setup()
    else:
        warn("Bỏ qua AI setup")

    # 5. Hướng dẫn test
    print_test_guide(customers, books)

    print("\nSeed data hoan tat!\n")
