# 🛍️ E-commerce Microservice Application

> Hệ thống thương mại điện tử đa ngành hàng theo kiến trúc **Microservice**, xây dựng với **Django REST Framework**, giao tiếp qua **HTTP REST** và **RabbitMQ**, triển khai bằng **Docker Compose**.

---

## 📑 Mục lục

1. [Tổng quan hệ thống](#-tổng-quan-hệ-thống)
2. [Kiến trúc hệ thống](#️-kiến-trúc-hệ-thống)
3. [Danh sách Services](#-danh-sách-services)
4. [Công nghệ sử dụng](#️-công-nghệ-sử-dụng)
5. [Cài đặt & Triển khai](#-cài-đặt--triển-khai)
6. [Biến môi trường](#️-biến-môi-trường)
7. [Giao tiếp giữa Services](#-giao-tiếp-giữa-services)
8. [Thiết kế Database](#️-thiết-kế-database)
9. [Luồng hoạt động chính](#-luồng-hoạt-động-chính)
10. [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
11. [Lệnh hữu ích](#-lệnh-hữu-ích)
12. [Troubleshooting](#-troubleshooting)
13. [Thông tin dự án](#-thông-tin-dự-án)

---

## 🔍 Tổng quan hệ thống

Ứng dụng e-commerce đa ngành hàng (sách, thời trang, điện tử, thực phẩm, đồ chơi, nội thất, mỹ phẩm, thể thao, văn phòng phẩm, điện gia dụng, trang sức, phụ kiện thú cưng...) được phân chia thành **~25 microservices** độc lập, mỗi service đảm nhiệm một domain nghiệp vụ hoặc một loại sản phẩm riêng.

**Tính năng chính:**
- 🛒 Storefront: duyệt sản phẩm, giỏ hàng, đặt hàng, theo dõi giao hàng
- 🧑‍💼 Admin panel: quản lý toàn bộ hệ thống (sản phẩm, khách hàng, nhân viên, đơn hàng…)
- 🔐 Xác thực JWT (auth-service) + Django session (api-gateway)
- ⭐ Đánh giá & bình luận sản phẩm
- 🤖 Hai AI service: **recommender-ai-service** (flan-t5 + ChromaDB) cho gợi ý sách, **ai-service** (Neo4j graph + RAG) cho phân tích quan hệ sản phẩm
- 💳 Thanh toán đa phương thức (COD, Banking, MoMo, VNPay)
- 🚚 Theo dõi vận chuyển (GHN, GHTK, Viettel Post, J&T)
- 📨 Xử lý đơn hàng bất đồng bộ qua RabbitMQ theo pattern **Saga / Choreography**

---

## 🏗️ Kiến trúc hệ thống

```
                         ┌───────────────────────────────┐
                         │           CLIENTS              │
                         │  Browser / Mobile / API Client │
                         └───────────────┬───────────────┘
                                         │ HTTP
                         ┌───────────────▼───────────────┐
                         │          API GATEWAY           │
                         │            :8000               │
                         │  SSR (Django Templates) +      │
                         │  Reverse proxy (requests)      │
                         └─┬────────────────────────────┬─┘
           ┌───────────────┘                            └───────────────┐
           │                                                            │
           ▼                                                            ▼
 ┌─────────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────────────┐
 │  AUTH (:8012)   │  │ Domain svc   │  │ Product    │  │ AI services          │
 │  JWT HS256      │  │ customer     │  │ book       │  │ recommender (:8011)  │
 │  auth_db        │  │ cart/order   │  │ clothe     │  │   flan-t5 + Chroma   │
 └─────────────────┘  │ pay/ship     │  │ electronic │  │ ai-service  (:8030)  │
                      │ staff/mgr    │  │ food, toy… │  │   Neo4j graph + RAG  │
                      │ catalog      │  │ (11 loại)  │  └──────────────────────┘
                      │ comment-rate │  └────────────┘
                      └──────────────┘

                      ┌──────────────── Async messaging ────────────────┐
                      │                                                  │
                      │   RabbitMQ (:5672, mgmt :15672)                  │
                      │      ├── order-worker   (order-service)          │
                      │      ├── pay-worker     (pay-service)            │
                      │      ├── ship-worker    (ship-service)           │
                      │      ├── cart-worker    (cart-service)           │
                      │      └── ai-ingest-worker (ai-service)           │
                      │                                                  │
                      │  Saga/Choreography:  order → pay → ship          │
                      │  Rollback flags: FORCE_PAYMENT_FAIL,              │
                      │                  FORCE_SHIPPING_FAIL              │
                      └──────────────────────────────────────────────────┘

 ┌───────────────────┐  ┌─────────────────────┐  ┌──────────────────┐
 │    MySQL 8.0      │  │    PostgreSQL 15    │  │     Neo4j 5      │
 │   host :3307      │  │      host :5433     │  │  :7474 / :7687   │
 │  bookstore_mysql  │  │  bookstore_postgres │  │  (graph cho      │
 │  customer_db      │  │  auth_db, order_db, │  │   ai-service)    │
 └───────────────────┘  │  staff/manager/     │  └──────────────────┘
                        │  catalog/pay/ship/  │
                        │  comment/recommender│
                        │  clothe_db…         │
                        └─────────────────────┘

 Công cụ quản trị:  phpMyAdmin :8080 · pgAdmin :8081 · RabbitMQ UI :15672
                    Neo4j Browser :7474
```

### Nguyên tắc thiết kế

| Nguyên tắc | Mô tả |
|-----------|-------|
| **Database per Service** | Mỗi service sở hữu DB riêng, không join cross-service |
| **API Gateway Pattern** | Mọi request từ client đi qua API Gateway |
| **Stateless Services** | Phần lớn service không giữ state, dễ scale |
| **Internal DNS** | Service gọi nhau qua tên container trong mạng Docker (port nội bộ `:8000`, khác host port) |
| **Async qua RabbitMQ** | Luồng đặt hàng dùng message broker để rollback Saga |
| **Health Checks** | MySQL, PostgreSQL, Neo4j, RabbitMQ có healthcheck trước khi dependent service khởi động |

---

## 📋 Danh sách Services

### Core domain services

| # | Service | Host port | DB | Vai trò |
|---|---------|-----------|------|---------|
| 1 | **api-gateway** | 8000 | Postgres `bookstore_postgres` | SSR UI + reverse proxy, session |
| 2 | **auth-service** | 8012 | Postgres `auth_db` | Cấp JWT (HS256) |
| 3 | **customer-service** | 8001 | MySQL `customer_db` | Thông tin khách hàng |
| 4 | **cart-service** | 8003 | Postgres `bookstore_postgres` | Giỏ hàng |
| 5 | **order-service** | 8004 | Postgres `order_db` | Đơn hàng |
| 6 | **pay-service** | 8008 | Postgres `pay_db` | Thanh toán |
| 7 | **ship-service** | 8009 | Postgres `ship_db` | Vận chuyển |
| 8 | **staff-service** | 8005 | Postgres `staff_db` | Nhân viên |
| 9 | **manager-service** | 8006 | Postgres `manager_db` | Quản lý cấp trên |
| 10 | **catalog-service** | 8007 | Postgres `catalog_db` | Danh mục sản phẩm |
| 11 | **comment-rate-service** | 8010 | Postgres `comment_db` | Đánh giá, bình luận |

### Product category services (mỗi loại một DB riêng)

| # | Service | Host port | DB |
|---|---------|-----------|------|
| 12 | **book-service** | 8002 | MySQL `bookstore_mysql` |
| 13 | **clothe-service** | 8013 | Postgres `clothe_db` |
| 14 | **electronic-service** | 8020 | Postgres `electronic_db` |
| 15 | **food-service** | 8021 | Postgres `food_db` |
| 16 | **toy-service** | 8022 | Postgres `toy_db` |
| 17 | **furniture-service** | 8023 | Postgres `furniture_db` |
| 18 | **cosmetic-service** | 8024 | Postgres `cosmetic_db` |
| 19 | **sport-service** | 8025 | Postgres `sport_db` |
| 20 | **stationery-service** | 8026 | Postgres `stationery_db` |
| 21 | **appliance-service** | 8027 | Postgres `appliance_db` |
| 22 | **jewelry-service** | 8028 | Postgres `jewelry_db` |
| 23 | **pet-supply-service** | 8029 | Postgres `pet_db` |

### AI / analytics

| # | Service | Host port | Storage | Vai trò |
|---|---------|-----------|---------|---------|
| 24 | **recommender-ai-service** | 8011 | Postgres `recommender_db` + volumes `recommender_models` (flan-t5), `recommender_chroma` (ChromaDB) | Gợi ý sách cá nhân hóa, RAG |
| 25 | **ai-service** | 8030 | Neo4j graph | Phân tích quan hệ sản phẩm, RAG qua graph |
| — | **ai-ingest-worker** | (worker) | → Neo4j | Consumer RabbitMQ, ingest dữ liệu vào graph |

### Workers (RabbitMQ consumers, không expose port)

| Worker | Build từ | Nhiệm vụ |
|--------|----------|---------|
| **cart-worker** | `./cart-service` | Xử lý event giỏ hàng (ví dụ clear sau khi order paid) |
| **order-worker** | `./order-service` | Điều phối Saga, cập nhật trạng thái đơn |
| **pay-worker** | `./pay-service` | Xử lý thanh toán, publish `payment.completed/failed`. Flag `FORCE_PAYMENT_FAIL=true` để test rollback |
| **ship-worker** | `./ship-service` | Tạo shipment khi thanh toán xong. Flag `FORCE_SHIPPING_FAIL=true` để test rollback |
| **ai-ingest-worker** | `./ai-service` | Ingest event vào Neo4j graph |

### Công cụ quản trị

| Công cụ | Port | Đăng nhập |
|---------|------|-----------|
| phpMyAdmin | 8080 | `bookstore_user` / `bookstore_pass` |
| pgAdmin | 8081 | `admin@admin.com` / `admin123` |
| RabbitMQ Management | 15672 | `guest` / `guest` |
| Neo4j Browser | 7474 | `neo4j` / `bookstore123` |

---

## 🛠️ Công nghệ sử dụng

### Backend
| Công nghệ | Mục đích |
|-----------|---------|
| Python 3.10 | Ngôn ngữ |
| Django 5.x + Django REST Framework | Web framework + REST API |
| PyMySQL + cryptography | Driver MySQL |
| psycopg2-binary | Driver PostgreSQL |
| pika | Client RabbitMQ |
| requests | HTTP client gọi nội bộ |
| PyJWT | Sinh/verify JWT (auth-service) |
| flan-t5 (HuggingFace) + ChromaDB | RAG cho recommender-ai-service |
| neo4j driver | Graph DB cho ai-service |
| gunicorn | WSGI production server |

### Frontend (API Gateway)
- Bootstrap 5.3.3 + Bootstrap Icons
- Django Templates (server-side rendering)

### Infrastructure
- Docker + Docker Compose v2
- MySQL 8.0, PostgreSQL 15, Neo4j 5, RabbitMQ 3 (management image)
- phpMyAdmin, pgAdmin

---

## 🚀 Cài đặt & Triển khai

### Yêu cầu

- **Docker Desktop** ≥ 4.x
- **RAM** tối thiểu 8GB (khuyến nghị 12GB — số lượng container lớn + Neo4j + RabbitMQ + model AI)
- **Disk** tối thiểu 10GB trống (volume model AI và Neo4j khá nặng)

### Khởi động lần đầu

```bash
# 1. Clone repository
git clone <repository-url>
cd django-ecommerce-microservices

# 2. (tùy chọn) đặt biến môi trường cho AI
export ANTHROPIC_API_KEY=sk-...        # macOS/Linux
# PowerShell: $env:ANTHROPIC_API_KEY="sk-..."

# 3. Build và khởi động
docker-compose up --build -d

# 4. Chờ 1–3 phút cho DB + RabbitMQ + Neo4j sẵn sàng
docker-compose ps

# 5. (tùy chọn) seed dữ liệu mẫu
python seed_data.py
```

### Truy cập

| URL | Mô tả |
|-----|-------|
| http://localhost:8000/ | Admin Dashboard |
| http://localhost:8000/store/ | Storefront khách hàng |
| http://localhost:8000/admin/ | Django Admin (cần superuser) |
| http://localhost:8080 | phpMyAdmin |
| http://localhost:8081 | pgAdmin |
| http://localhost:15672 | RabbitMQ Management |
| http://localhost:7474 | Neo4j Browser |
| http://localhost:80XX/ | Truy cập trực tiếp từng service API |

### Start lại sau khi tắt máy

```bash
docker-compose up -d          # không cần --build
docker-compose ps
```

---

## ⚙️ Biến môi trường

Tất cả biến cấu hình trong `docker-compose.yml` (không cần `.env` trừ `ANTHROPIC_API_KEY`).

### Database chung

| Biến | Giá trị | Dùng cho |
|------|---------|---------|
| `MYSQL_ROOT_PASSWORD` | `rootpassword` | MySQL root |
| `MYSQL_USER` / `MYSQL_PASSWORD` | `bookstore_user` / `bookstore_pass` | MySQL app |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `bookstore_user` / `bookstore_pass` | PostgreSQL |
| `POSTGRES_DB` | `bookstore_postgres` | DB mặc định Postgres |
| `NEO4J_AUTH` | `neo4j/bookstore123` | Neo4j |

### Mỗi service đọc cấu hình DB theo pattern

```yaml
environment:
  - DB_ENGINE=django.db.backends.postgresql   # hoặc mysql
  - DB_NAME=<service>_db
  - DB_USER=bookstore_user
  - DB_PASSWORD=bookstore_pass
  - DB_HOST=postgres-db                       # hoặc mysql-db
  - DB_PORT=5432                              # 3306 với MySQL
```

### Biến đặc thù

| Biến | Service | Ý nghĩa |
|------|---------|--------|
| `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE` | auth-service, api-gateway | Phải khớp để verify token |
| `AUTH_SERVICE_URL` | api-gateway | URL nội bộ của auth-service |
| `RABBITMQ_HOST` | gateway, workers, ai-service | Hostname RabbitMQ (`rabbitmq`) |
| `FORCE_PAYMENT_FAIL` | pay-worker | `true` để test rollback Saga |
| `FORCE_SHIPPING_FAIL` | ship-worker | `true` để test rollback Saga |
| `AI_MODEL_DIR`, `CHROMA_DB_DIR` | recommender-ai-service | Thư mục chứa model & vector DB |
| `ANTHROPIC_API_KEY` | recommender-ai-service | Tùy chọn, fallback Claude API |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | ai-service, ai-ingest-worker | Kết nối Neo4j |
| `BOOK_SERVICE_URL`, `ORDER_SERVICE_URL`,… | recommender-ai-service | URL nội bộ các service phụ thuộc |

---

## 🔗 Giao tiếp giữa Services

### Đồng bộ — HTTP REST

- Service gọi nhau qua **tên container + port nội bộ `:8000`** (không phải host port).
- Ví dụ: `http://book-service:8000/books/`, `http://auth-service:8000/verify/`.
- URL service cấu hình trong `api-gateway/api_gateway/views.py` (hằng số) và qua env var ở các service khác.

### Bất đồng bộ — RabbitMQ (Saga / Choreography)

Luồng đặt hàng chạy bất đồng bộ:

```
Client → api-gateway /store/checkout/
                │
                ▼ (HTTP)
           order-service POST /orders/
                │ publish "order.created"
                ▼
            RabbitMQ ──► pay-worker   (tạo Payment, charge)
                              │ publish "payment.completed" / "payment.failed"
                              ▼
            RabbitMQ ──► ship-worker  (nếu paid → tạo Shipment)
                              │ publish "shipment.created" / "shipment.failed"
                              ▼
            RabbitMQ ──► order-worker (cập nhật order.status)
                        cart-worker  (clear cart khi paid)
```

Mỗi service có `app/consumer.py` chạy như process riêng. Khi sửa schema message phải cập nhật cả producer và consumer ở cả hai phía.

---

## 🗄️ Thiết kế Database

### MySQL (host `:3307` / internal `mysql-db:3306`)
| Database | Service | Ghi chú |
|----------|---------|--------|
| `bookstore_mysql` | book-service | Catalog sách |
| `customer_db` | customer-service | Khách hàng |

> Tạo qua `init-scripts/init-customer-db.sql`.

### PostgreSQL (host `:5433` / internal `postgres-db:5432`)
| Database | Service |
|----------|---------|
| `bookstore_postgres` | cart-service, api-gateway (session) |
| `auth_db` | auth-service |
| `order_db` | order-service |
| `staff_db` | staff-service |
| `manager_db` | manager-service |
| `catalog_db` | catalog-service |
| `pay_db` | pay-service |
| `ship_db` | ship-service |
| `comment_db` | comment-rate-service |
| `recommender_db` | recommender-ai-service |
| `clothe_db`, `electronic_db`, `food_db`, `toy_db`, `furniture_db`, `cosmetic_db`, `sport_db`, `stationery_db`, `appliance_db`, `jewelry_db`, `pet_db` | Các product category services |

> `init-scripts/init-order-db.sh` tạo các DB Postgres phụ (trừ `bookstore_postgres` mặc định). Script chỉ chạy **lần đầu** khi volume được tạo. Nếu thêm service mới có DB riêng, cần cập nhật script **và** tạo DB thủ công nếu volume đã tồn tại.

### Neo4j (host `:7474` HTTP, `:7687` Bolt)
- Chứa graph quan hệ sản phẩm–khách hàng–đơn hàng cho **ai-service**.
- Plugin APOC được bật sẵn.

---

## 🔄 Luồng hoạt động chính

### 1. Đăng nhập (JWT qua auth-service)

```
Khách hàng → /store/login/ (api-gateway)
              │
              ├─► auth-service POST /login/   body: {email, password}
              │       ↳ trả về JWT HS256 (iss/aud khớp gateway)
              │
              ▼
     api-gateway lưu JWT + customer info vào Django session
              │
              ▼
     Redirect → /store/
```

### 2. Checkout (Saga qua RabbitMQ)

```
/store/checkout/  (api-gateway)
    ├─ 1. Validate cart       (cart-service, HTTP)
    ├─ 2. Check stock         (<category>-service, HTTP)
    ├─ 3. Tạo Order           (order-service, HTTP)
    └─ 4. Publish "order.created" (RabbitMQ)
              │
              ▼
         pay-worker → charge → publish "payment.completed/failed"
              │
              ▼
         ship-worker → nếu paid: tạo shipment → "shipment.created"
              │                nếu fail:  "payment.refund.request" → rollback
              ▼
         order-worker cập nhật trạng thái cuối
         cart-worker clear giỏ nếu paid
```

Test rollback: bật `FORCE_PAYMENT_FAIL=true` hoặc `FORCE_SHIPPING_FAIL=true` trên worker tương ứng.

### 3. Gợi ý sách AI (recommender-ai-service, stateless)

```
/store/  → GET /recommendations/{customer_id}/ (recommender)
            ├─ Gọi order-service      → lịch sử mua
            ├─ Gọi book-service       → catalog
            ├─ Gọi comment-rate-svc   → rating
            ├─ Truy ChromaDB          → semantic similarity
            ├─ (tùy chọn) flan-t5 / Claude → giải thích gợi ý
            └─ Trả top N
```

### 4. Graph RAG (ai-service, Neo4j)

```
Event (order, review, view) ──► RabbitMQ ──► ai-ingest-worker
                                                      │ upsert nodes/edges
                                                      ▼
                                                   Neo4j
                                                      ▲
                                  ai-service (HTTP) ──┘  truy vấn graph phục vụ RAG
```

---

## 📁 Cấu trúc thư mục

```
django-ecommerce-microservices/
├── docker-compose.yml              # Orchestration toàn hệ thống
├── README.md                       # Tài liệu này
├── CLAUDE.md                       # Hướng dẫn cho Claude Code
├── seed_data.py                    # Seed dữ liệu mẫu
├── load-tests/                     # Kịch bản load test
│
├── init-scripts/
│   ├── init-customer-db.sql        # MySQL: tạo customer_db
│   └── init-order-db.sh            # PostgreSQL: tạo các DB phụ
│
├── api-gateway/                    # SSR UI + reverse proxy
├── auth-service/                   # JWT
│
├── customer-service/               # MySQL
├── book-service/                   # MySQL
│
├── cart-service/                   # + cart-worker (consumer.py)
├── order-service/                  # + order-worker
├── pay-service/                    # + pay-worker
├── ship-service/                   # + ship-worker
│
├── staff-service/    manager-service/    catalog-service/
├── comment-rate-service/
│
├── clothe-service/   electronic-service/ food-service/
├── toy-service/      furniture-service/  cosmetic-service/
├── sport-service/    stationery-service/ appliance-service/
├── jewelry-service/  pet-supply-service/
│
├── recommender-ai-service/         # flan-t5 + ChromaDB
└── ai-service/                     # Neo4j graph + ai-ingest-worker
```

### Cấu trúc chuẩn một service

```
<service>/
├── Dockerfile
├── manage.py
├── requirements.txt
├── <service>_service/              # settings.py, urls.py, wsgi.py
└── app/
    ├── models.py  serializers.py  views.py  urls.py
    ├── admin.py   migrations/
    └── consumer.py                 # (nếu là worker / consumer RabbitMQ)
```

App label Django luôn là `app`, nên lệnh migrations là `python manage.py makemigrations app`.

---

## 🔧 Lệnh hữu ích

### Khởi động / dừng

```bash
docker-compose up --build -d                       # fresh install
docker-compose up -d                               # start lại
docker-compose down                                # dừng, giữ volume
docker-compose down -v                             # ⚠️ xóa toàn bộ volume (reset DB)
docker-compose up --build -d book-service          # rebuild 1 service
docker-compose restart pay-worker ship-worker      # restart worker
```

### Logs

```bash
docker-compose logs -f                             # tất cả
docker-compose logs -f api-gateway
docker-compose logs -f order-worker pay-worker ship-worker
docker-compose logs --tail=50 recommender-ai-service
docker-compose logs -f --since="5m" ai-service
```

### Django trong container

```bash
# Migrations
docker-compose exec book-service python manage.py makemigrations app
docker-compose exec book-service python manage.py migrate

# Test
docker-compose exec order-service python manage.py test app
docker-compose exec order-service python manage.py test app.tests.OrderFlowTest.test_saga_rollback

# Superuser
docker-compose exec api-gateway python manage.py createsuperuser
```

### Database

```bash
# PostgreSQL
docker exec -it django-ecommerce-microservices-postgres-db-1 \
  psql -U bookstore_user -d order_db
docker exec django-ecommerce-microservices-postgres-db-1 \
  psql -U bookstore_user -l

# MySQL
docker exec -it django-ecommerce-microservices-mysql-db-1 \
  mysql -u bookstore_user -pbookstore_pass

# Neo4j Cypher shell
docker exec -it django-ecommerce-microservices-neo4j-1 \
  cypher-shell -u neo4j -p bookstore123
```

> Tên container có thể khác tùy `COMPOSE_PROJECT_NAME` — kiểm tra bằng `docker-compose ps`.

### Tạo thủ công các DB Postgres còn thiếu

Chạy khi volume Postgres đã tồn tại mà thiếu DB (ví dụ khi thêm service mới):

```bash
for db in auth_db staff_db manager_db catalog_db pay_db ship_db comment_db recommender_db order_db clothe_db electronic_db food_db toy_db furniture_db cosmetic_db sport_db stationery_db appliance_db jewelry_db pet_db; do
  docker exec django-ecommerce-microservices-postgres-db-1 \
    psql -U bookstore_user -d bookstore_postgres \
    -c "CREATE DATABASE $db OWNER bookstore_user"
done
```

> `CREATE DATABASE` không chạy trong transaction block → phải tạo từng DB.

### RabbitMQ

```bash
# Xem queues
docker exec django-ecommerce-microservices-rabbitmq-1 \
  rabbitmqctl list_queues name messages consumers

# Purge 1 queue (để test lại)
docker exec django-ecommerce-microservices-rabbitmq-1 \
  rabbitmqctl purge_queue order.created
```

---

## 🔎 Troubleshooting

### ❌ `database "xxx_db" does not exist`
Init script chỉ chạy lần đầu. Tạo thủ công theo lệnh ở mục trên.

### ❌ Service `Exited (1)` ngay sau start

```bash
docker-compose logs --tail=30 <service>
```

| Log | Nguyên nhân | Giải pháp |
|-----|------------|-----------|
| `database "..." does not exist` | DB chưa tạo | Tạo DB thủ công |
| `could not connect to server` | DB chưa healthy | Chờ 30s rồi `up -d <service>` |
| `ModuleNotFoundError` | Thiếu package | `up --build -d <service>` |
| `Port already in use` | Host port bị chiếm | Đổi host port trong `docker-compose.yml` |
| `ConnectionRefusedError ... 5672` | RabbitMQ chưa sẵn | Đợi health rồi restart worker |
| `Neo.ClientError.Security.Unauthorized` | Sai mật khẩu Neo4j | Kiểm tra `NEO4J_AUTH` và env của ai-service |

### ❌ JWT `invalid signature` / `audience mismatch`
`JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE` ở **auth-service** và **api-gateway** phải trùng.

### ❌ Worker không nhận message
- Kiểm tra `docker-compose logs rabbitmq` xem đã healthy chưa.
- RabbitMQ UI :15672 → tab Queues xem có binding & consumer hay không.
- Đảm bảo producer và consumer dùng cùng tên exchange/queue/routing key.

### ❌ Service gọi nhau không kết nối được

```bash
docker network inspect django-ecommerce-microservices_default \
  --format='{{range .Containers}}{{.Name}} {{end}}'
```

Nếu thiếu: `docker-compose up -d <service>`.

### 🔄 Reset toàn bộ

```bash
docker-compose down -v --remove-orphans
docker system prune -f
docker-compose up --build -d
```

> ⚠️ Sẽ xóa toàn bộ dữ liệu: MySQL, PostgreSQL, Neo4j, model AI, ChromaDB.

---

## 📌 Thông tin dự án

| Thuộc tính | Giá trị |
|------------|---------|
| **Kiến trúc** | Microservice + Saga (Choreography) |
| **Số services** | ~25 (11 domain + 12 product category + 2 AI) |
| **Workers** | 5 (cart, order, pay, ship, ai-ingest) |
| **Tổng containers** | ≈ 34 (services + workers + MySQL + Postgres + Neo4j + RabbitMQ + phpMyAdmin + pgAdmin) |
| **Framework** | Django 5.x + Django REST Framework |
| **Frontend** | Bootstrap 5.3.3 (SSR) |
| **Databases** | MySQL 8.0, PostgreSQL 15, Neo4j 5 |
| **Message broker** | RabbitMQ 3 |
| **Auth** | JWT HS256 (auth-service) + Django session (gateway) |
| **AI** | flan-t5 + ChromaDB (recommender) · Neo4j graph RAG (ai-service) |
| **Ngôn ngữ** | Python 3.10 |
