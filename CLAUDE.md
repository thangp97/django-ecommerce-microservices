# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan

Hệ thống e-commerce sách theo kiến trúc microservice, mỗi service là một Django project độc lập, chạy qua Docker Compose. Tất cả services build từ thư mục riêng với cấu trúc giống nhau: `manage.py`, `<service>_service/` (settings), `app/` (models, views, urls, serializers).

## Lệnh thường dùng

```bash
# Khởi động toàn bộ hệ thống
docker-compose up --build

# Khởi động 1 service (và phụ thuộc)
docker-compose up <service-name>

# Xem log 1 service
docker-compose logs -f <service-name>

# Chạy lệnh Django trong container đang chạy
docker-compose exec <service-name> python manage.py <command>

# Migrations (thường tự chạy qua command trong compose, nhưng khi cần thủ công)
docker-compose exec <service-name> python manage.py makemigrations app
docker-compose exec <service-name> python manage.py migrate

# Chạy test của 1 service
docker-compose exec <service-name> python manage.py test app

# Chạy 1 test cụ thể
docker-compose exec <service-name> python manage.py test app.tests.TestClass.test_method

# Seed data mẫu (script ở root)
python seed_data.py

# Load tests
# xem thư mục load-tests/
```

Truy cập:
- API Gateway (UI + proxy): http://localhost:8000
- phpMyAdmin: http://localhost:8080 · pgAdmin: http://localhost:8081 (admin@admin.com / admin123)
- RabbitMQ management: http://localhost:15672 (guest/guest)

## Kiến trúc

### Thành phần chính

- **api-gateway** (:8000) – Django + Bootstrap templates. Vừa là reverse proxy (`requests` tới các service nội bộ), vừa SSR storefront và admin UI. Auth là **session-based**, session lưu trong PostgreSQL `bookstore_postgres`. URL service cấu hình cứng trong `api_gateway/views.py`.
- **auth-service** (:8012) – cấp JWT (HS256). `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE` phải khớp với gateway.
- **Domain services**: customer (:8001, MySQL), book (:8002, MySQL), clothe (:8013), cart (:8003), order (:8004), staff (:8005), manager (:8006), catalog (:8007), pay (:8008), ship (:8009), comment-rate (:8010).
- **recommender-ai-service** (:8011) – **stateless**, tổng hợp dữ liệu realtime từ book/order/comment-rate/customer services. Dùng model local (flan-t5) + ChromaDB, volumes `recommender_models` & `recommender_chroma`. Biến env `ANTHROPIC_API_KEY` tùy chọn.

### Giao tiếp

- **Đồng bộ**: HTTP REST giữa các service qua DNS Docker (tên service:8000 trong mạng nội bộ — lưu ý khác với host port).
- **Bất đồng bộ**: RabbitMQ (:5672) cho luồng đặt hàng — mỗi service có `app/consumer.py` chạy trong worker riêng (`cart-worker`, `order-worker`, `pay-worker`, `ship-worker`). Saga/choreography: order → pay → ship. Flag `FORCE_PAYMENT_FAIL`, `FORCE_SHIPPING_FAIL` trên worker để test rollback.

### Database

- **MySQL 8.0** (host :3307): `bookstore_mysql` (book), `customer_db`. Init: `init-scripts/init-customer-db.sql`.
- **PostgreSQL 15** (host :5433): `bookstore_postgres` (cart + gateway session), `auth_db`, `order_db`, `staff_db`, `manager_db`, `catalog_db`, `pay_db`, `ship_db`, `comment_db`, `recommender_db`, `clothe_db`. Init: `init-scripts/init-order-db.sh` (tạo các DB postgres khác).
- Mỗi service chỉ owns DB của mình — **không join cross-service**, thay vào đó gọi HTTP.

### Cấu trúc 1 service (mẫu)

```
<service>/
  Dockerfile
  manage.py
  requirements.txt
  <service>_service/   # settings.py, urls.py, wsgi.py
  app/                 # models.py, views.py, urls.py, serializers.py, (consumer.py nếu có worker)
```

DB config đọc từ env `DB_ENGINE/DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT` (xem `docker-compose.yml`).

## Lưu ý khi sửa code

- Khi thêm model mới, chạy `makemigrations app` (app label luôn là `app`) rồi `migrate` trong container.
- Khi thay đổi URL/port 1 service: cập nhật cả `docker-compose.yml` **và** hằng số URL trong `api-gateway/api_gateway/views.py`.
- Không mock cross-service call trong code thật — gateway và recommender đều phụ thuộc các service khác đang chạy; khi dev local cần `docker-compose up` đủ dependencies.
- Worker consumer (`app/consumer.py`) chạy như process riêng biệt — sửa message schema phải đồng bộ producer + consumer cả 2 phía.
