from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
import requests
import os
from math import ceil
from .behavior_publisher import publish_event

BOOK_SERVICE_URL = "http://book-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
STAFF_SERVICE_URL = "http://staff-service:8000"
MANAGER_SERVICE_URL = "http://manager-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"
RECOMMENDER_SERVICE_URL = "http://recommender-ai-service:8000"
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
CLOTHE_SERVICE_URL = "http://clothe-service:8000"
ELECTRONIC_SERVICE_URL = "http://electronic-service:8000"
FOOD_SERVICE_URL = "http://food-service:8000"
TOY_SERVICE_URL = "http://toy-service:8000"
FURNITURE_SERVICE_URL = "http://furniture-service:8000"
COSMETIC_SERVICE_URL = "http://cosmetic-service:8000"
SPORT_SERVICE_URL = "http://sport-service:8000"
STATIONERY_SERVICE_URL = "http://stationery-service:8000"
APPLIANCE_SERVICE_URL = "http://appliance-service:8000"
JEWELRY_SERVICE_URL = "http://jewelry-service:8000"
PET_SUPPLY_SERVICE_URL = "http://pet-supply-service:8000"

# Map product_type -> (service URL, URL plural). Dùng chung cho cart/order proxy.
PRODUCT_SERVICE_MAP = {
    "book": (BOOK_SERVICE_URL, "books"),
    "clothe": (CLOTHE_SERVICE_URL, "clothes"),
    "electronic": (ELECTRONIC_SERVICE_URL, "electronics"),
    "food": (FOOD_SERVICE_URL, "foods"),
    "toy": (TOY_SERVICE_URL, "toys"),
    "furniture": (FURNITURE_SERVICE_URL, "furnitures"),
    "cosmetic": (COSMETIC_SERVICE_URL, "cosmetics"),
    "sport": (SPORT_SERVICE_URL, "sports"),
    "stationery": (STATIONERY_SERVICE_URL, "stationeries"),
    "appliance": (APPLIANCE_SERVICE_URL, "appliances"),
    "jewelry": (JEWELRY_SERVICE_URL, "jewelries"),
    "pet-supply": (PET_SUPPLY_SERVICE_URL, "pet-supplies"),
}

PRODUCT_TYPE_META = {
    "book": {"label": "Sach", "subtitle_key": "author"},
    "clothe": {"label": "Thoi trang", "subtitle_key": "material"},
    "electronic": {"label": "Dien tu", "subtitle_key": "brand"},
    "food": {"label": "Thuc pham", "subtitle_key": "category"},
    "toy": {"label": "Do choi", "subtitle_key": "category"},
    "furniture": {"label": "Noi that", "subtitle_key": "material"},
    "cosmetic": {"label": "My pham", "subtitle_key": "brand"},
    "sport": {"label": "The thao", "subtitle_key": "category"},
    "stationery": {"label": "Van phong pham", "subtitle_key": "category"},
    "appliance": {"label": "Gia dung", "subtitle_key": "brand"},
    "jewelry": {"label": "Trang suc", "subtitle_key": "material"},
    "pet-supply": {"label": "Do thu cung", "subtitle_key": "category"},
}


def _get_product_label(product_type):
    return PRODUCT_TYPE_META.get(product_type, {}).get("label", product_type)


def _build_store_product_detail_url(product_type, product_id):
    if product_type == "book":
        return f"/store/book/{product_id}/"
    if product_type == "clothe":
        return f"/store/clothes/{product_id}/"
    return f"/store/products/{product_type}/{product_id}/"


# ── HELPERS ──────────────────────────────────────────────────

def product_api_proxy(request, product_type, pk=None):
    """Generic JSON proxy: /api/products/<type>/ và /api/products/<type>/<pk>/.
    Map product_type -> service URL qua PRODUCT_SERVICE_MAP."""
    entry = PRODUCT_SERVICE_MAP.get(product_type)
    if not entry:
        return JsonResponse({"error": f"Unknown product_type '{product_type}'"}, status=404)
    base_url, plural = entry
    url = f"{base_url}/{plural}/" + (f"{pk}/" if pk else "")
    try:
        if request.method == "GET":
            r = requests.get(url, timeout=5)
        elif request.method == "POST":
            r = requests.post(url, json=request.POST.dict() or None, timeout=5)
        elif request.method == "PATCH":
            r = requests.patch(url, json=request.POST.dict() or None, timeout=5)
        else:
            return JsonResponse({"error": "Method not allowed"}, status=405)
        return JsonResponse(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}, safe=False, status=r.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=502)


def is_staff_check(user):
    return user.is_staff


def _get_store_customer(request):
    cid = request.session.get("customer_id")
    if cid:
        return {"id": cid, "name": request.session.get("customer_name", "")}
    return None


def _enrich_order_items(items):
    # Gắn title/author/image_url vào từng order item dựa trên product_type.
    cache = {}
    for item in items:
        ptype = item.get("product_type", "book")
        pid = item.get("product_id", item.get("book_id"))
        entry = PRODUCT_SERVICE_MAP.get(ptype)
        product = {}
        if entry and pid is not None:
            key = (ptype, pid)
            if key in cache:
                product = cache[key]
            else:
                base_url, plural = entry
                try:
                    rp = requests.get(f"{base_url}/{plural}/{pid}/", timeout=3)
                    if rp.status_code == 200:
                        product = rp.json()
                except Exception:
                    pass
                cache[key] = product
        title = product.get("title") or product.get("name") or f"{ptype} #{pid}"
        author = product.get("author") or product.get("brand") or product.get("material") or product.get("category") or ""
        detail_url = _build_store_product_detail_url(ptype, pid)
        item["item_title"] = title
        item["item_subtitle"] = author
        item["detail_url"] = detail_url
        item["product_label"] = _get_product_label(ptype)
        item["book_title"] = title
        item["book_author"] = author
        item["image_url"] = product.get("image_url") or f"https://loremflickr.com/100/140/{ptype}?lock={pid}"


def _get_cart_id(customer_id):
    try:
        r = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/", timeout=3)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "cart_id" in data:
                return data["cart_id"]

        # Fallback for first-time customers or transient desync: explicitly create cart.
        r_create = requests.post(
            f"{CART_SERVICE_URL}/carts/",
            json={"customer_id": customer_id},
            timeout=3,
        )
        if r_create.status_code in (200, 201):
            created = r_create.json()
            if isinstance(created, dict) and "id" in created:
                return created["id"]

        # Final retry to handle race conditions.
        r_retry = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/", timeout=3)
        if r_retry.status_code == 200:
            data = r_retry.json()
            if isinstance(data, dict) and "cart_id" in data:
                return data["cart_id"]
    except Exception:
        pass
    return None


# ── ADMIN VIEWS ──────────────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def home(request):
    try:
        books = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=3).json()
    except Exception:
        books = []
    try:
        customers = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=3).json()
    except Exception:
        customers = []
    try:
        orders = requests.get(f"{ORDER_SERVICE_URL}/orders/", timeout=3).json()
    except Exception:
        orders = []
    try:
        staff = requests.get(f"{STAFF_SERVICE_URL}/staff/", timeout=3).json()
    except Exception:
        staff = []
    try:
        managers = requests.get(f"{MANAGER_SERVICE_URL}/managers/", timeout=3).json()
    except Exception:
        managers = []
    try:
        payments = requests.get(f"{PAY_SERVICE_URL}/payments/", timeout=3).json()
    except Exception:
        payments = []
    try:
        shipments = requests.get(f"{SHIP_SERVICE_URL}/shipments/", timeout=3).json()
    except Exception:
        shipments = []
    return render(request, "home.html", {
        "total_books": len(books) if isinstance(books, list) else 0,
        "total_customers": len(customers) if isinstance(customers, list) else 0,
        "total_orders": len(orders) if isinstance(orders, list) else 0,
        "total_staff": len(staff) if isinstance(staff, list) else 0,
        "total_managers": len(managers) if isinstance(managers, list) else 0,
        "total_payments": len(payments) if isinstance(payments, list) else 0,
        "total_shipments": len(shipments) if isinstance(shipments, list) else 0,
    })


@user_passes_test(is_staff_check, login_url='/admin/login/')
def book_list(request):
    error = None
    books = []
    if request.method == "POST":
        data = {
            "title": request.POST.get("title"),
            "author": request.POST.get("author"),
            "price": request.POST.get("price"),
            "stock": request.POST.get("stock"),
        }
        try:
            r = requests.post(f"{BOOK_SERVICE_URL}/books/", json=data, timeout=3)
            if r.status_code in (200, 201):
                messages.success(request, "Thêm sách thành công!")
            else:
                messages.error(request, f"Lỗi: {r.text}")
        except Exception as e:
            messages.error(request, f"Không kết nối được book-service: {e}")
        return redirect("book_list")
    try:
        r = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=3)
        books = r.json()
        if not isinstance(books, list):
            books = []
    except Exception as e:
        error = str(e)
    return render(request, "books.html", {"books": books, "error": error})


@user_passes_test(is_staff_check, login_url='/admin/login/')
def customer_list(request):
    error = None
    customers = []
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "email": request.POST.get("email"),
        }
        try:
            r = requests.post(f"{CUSTOMER_SERVICE_URL}/customers/", json=data, timeout=3)
            if r.status_code in (200, 201):
                messages.success(request, "Thêm khách hàng thành công!")
            else:
                messages.error(request, f"Lỗi: {r.text}")
        except Exception as e:
            messages.error(request, f"Không kết nối được customer-service: {e}")
        return redirect("customer_list")
    try:
        r = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=3)
        customers = r.json()
        if not isinstance(customers, list):
            customers = []
    except Exception as e:
        error = str(e)
    return render(request, "customers.html", {"customers": customers, "error": error})


@user_passes_test(is_staff_check, login_url='/admin/login/')
def view_cart(request, customer_id):
    error = None
    items = []
    cart_id = None
    cart_error = None
    if request.method == "POST":
        data = {
            "cart": request.POST.get("cart_id"),
            "product_id": request.POST.get("product_id") or request.POST.get("book_id"),
            "product_type": request.POST.get("product_type", "book"),
            "quantity": request.POST.get("quantity"),
        }
        try:
            r = requests.post(f"{CART_SERVICE_URL}/cart-items/", json=data, timeout=3)
            if r.status_code in (200, 201):
                messages.success(request, "Thêm vào giỏ hàng thành công!")
            else:
                messages.error(request, f"Lỗi: {r.text}")
        except Exception as e:
            messages.error(request, f"Không kết nối được cart-service: {e}")
        return redirect("view_cart", customer_id=customer_id)
    try:
        r = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/", timeout=3)
        data = r.json()
        if isinstance(data, dict) and "cart_id" in data:
            cart_id = data["cart_id"]
            items = data.get("items", [])
        elif isinstance(data, dict) and "error" in data:
            cart_error = data["error"]
    except Exception as e:
        error = str(e)
    try:
        books = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=3).json()
        if not isinstance(books, list):
            books = []
    except Exception:
        books = []
    return render(request, "cart.html", {
        "items": items, "customer_id": customer_id, "cart_id": cart_id,
        "books": books, "error": error, "cart_error": cart_error,
    })


# ── STOREFRONT VIEWS ─────────────────────────────────────────

def store_home(request):
    customer = _get_store_customer(request)
    recommendations = []
    ai_search_answer = ""
    ai_search_recommendations = []
    q = request.GET.get("q", "").strip()

    if q:
        if customer:
            publish_event('search', customer['id'], query=q, routing_key='search')

    # AI search suggestions from ai-service when customer clicks Search.
    if q:
        ai_url = os.environ.get('AI_SERVICE_URL', 'http://ai-service:8000')
        ai_payload = {"message": q}
        if customer:
            ai_payload["user_id"] = customer["id"]
        try:
            r_ai = requests.post(f"{ai_url}/chat/", json=ai_payload, timeout=8)
            if r_ai.status_code == 200:
                ai_data = r_ai.json()
                ai_search_answer = ai_data.get("answer", "") or ""
                ai_recs = ai_data.get("recommended_products", [])
                if isinstance(ai_recs, list):
                    for rec in ai_recs:
                        ptype = rec.get("product_type")
                        pid = rec.get("product_id")
                        if ptype in PRODUCT_SERVICE_MAP and pid is not None:
                            rec["detail_url"] = _build_store_product_detail_url(ptype, pid)
                            rec["product_label"] = _get_product_label(ptype)
                            ai_search_recommendations.append(rec)
        except Exception:
            pass

    # Multi-category products from all product services.
    all_products = []
    total_products_all = 0
    in_stock_products_all = 0
    for ptype, (base_url, plural) in PRODUCT_SERVICE_MAP.items():
        try:
            rp = requests.get(f"{base_url}/{plural}/", timeout=3)
            items = rp.json() if rp.status_code == 200 else []
        except Exception:
            items = []
        if not isinstance(items, list):
            items = []

        normalized = []
        for item in items:
            pid = item.get("id")
            if pid is None:
                continue
            title = item.get("title") or item.get("name") or f"{_get_product_label(ptype)} #{pid}"
            subtitle = (
                item.get("author")
                or item.get("brand")
                or item.get("material")
                or item.get("category")
                or ""
            )
            try:
                price = float(item.get("price", 0) or 0)
            except (TypeError, ValueError):
                price = 0.0
            stock_value = int(item.get("stock", 0) or 0)
            normalized_item = {
                "id": pid,
                "name": title,
                "subtitle": subtitle,
                "price": price,
                "stock": stock_value,
                "product_type": ptype,
                "product_label": _get_product_label(ptype),
                "detail_url": _build_store_product_detail_url(ptype, pid),
            }
            normalized.append(normalized_item)
            all_products.append(normalized_item)

        total_products_all += len(normalized)
        in_stock_products_all += sum(1 for p in normalized if p["stock"] > 0)

    q_lower = q.lower()
    searched_products = []
    for product in all_products:
        haystack = " ".join([
            str(product.get("name", "")),
            str(product.get("subtitle", "")),
            str(product.get("product_label", "")),
            str(product.get("product_type", "")),
        ]).lower()
        if not q_lower or q_lower in haystack:
            searched_products.append(product)

    searched_products.sort(
        key=lambda x: (
            x["stock"] <= 0,
            x["product_label"],
            -int(x["id"] or 0),
        )
    )

    total_results = len(searched_products)
    displayed_products = searched_products[:24]

    graph_recommendations = []
    if customer:
        # Legacy recommender (giữ tương thích với store_home cũ)
        try:
            r = requests.get(f"{RECOMMENDER_SERVICE_URL}/recommendations/{customer['id']}/", timeout=5)
            if r.status_code == 200:
                recommendations = r.json().get("recommendations", [])
        except Exception:
            pass
        # GraphRAG co-occurrence từ ai-service (multi-product-type)
        try:
            ai_url = os.environ.get('AI_SERVICE_URL', 'http://ai-service:8000')
            r = requests.get(f"{ai_url}/recommend/",
                             params={'user_id': customer['id'], 'limit': 6}, timeout=3)
            if r.status_code == 200:
                graph_recommendations = r.json().get('recommendations', [])
        except Exception:
            pass
    return render(request, "store_home.html", {
        "customer": customer,
        "recommendations": recommendations,
        "graph_recommendations": graph_recommendations,
        "ai_search_answer": ai_search_answer,
        "ai_search_recommendations": ai_search_recommendations,
        "all_products_preview": all_products[:12],
        "displayed_products": displayed_products,
        "total_products_all": total_products_all,
        "in_stock_products_all": in_stock_products_all,
        "total_results": total_results,
        "filters": {
            "q": q,
        },
        "product_types": [
            {
                "key": ptype,
                "label": _get_product_label(ptype),
                "url": f"/store/products/{ptype}/" if ptype not in ("book", "clothe")
                else ("/store/" if ptype == "book" else "/store/clothes/"),
            }
            for ptype in PRODUCT_SERVICE_MAP.keys()
        ],
    })


def store_login(request):
    if _get_store_customer(request):
        return redirect("store_home")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        try:
            r = requests.post(f"{CUSTOMER_SERVICE_URL}/customers/login/", 
                              json={"email": email, "password": password}, timeout=3)
            if r.status_code == 200:
                try:
                    found = r.json()
                    request.session["customer_id"] = found["id"]
                    request.session["customer_name"] = found["name"]

                    # Central auth-service token issuance.
                    try:
                        r_auth = requests.post(
                            f"{AUTH_SERVICE_URL}/auth/login/",
                            json={"email": email, "password": password},
                            timeout=3,
                        )
                        if r_auth.status_code == 200:
                            request.session["access_token"] = r_auth.json().get("access", "")
                    except Exception:
                        pass

                    messages.success(request, f"Xin chào, {found['name']}!")
                    return redirect("store_home")
                except ValueError:
                    messages.error(request, "Lỗi phản hồi từ hệ thống xác thực (Invalid JSON).")
            else:
                try:
                    error_msg = r.json().get("error", "Email hoặc mật khẩu không đúng.")
                except ValueError:
                    error_msg = f"Lỗi hệ thống ({r.status_code}). Vui lòng thử lại sau."
                messages.error(request, error_msg)
        except Exception as e:
            messages.error(request, f"Lỗi kết nối: {e}")
    return render(request, "store_login.html", {"customer": None})


def store_register(request):
    if _get_store_customer(request):
        return redirect("store_home")
    if request.method == "POST":
        data = {
            "name": request.POST.get("name", "").strip(),
            "email": request.POST.get("email", "").strip(),
            "password": request.POST.get("password", ""),
        }
        try:
            r = requests.post(f"{CUSTOMER_SERVICE_URL}/customers/", json=data, timeout=3)
            if r.status_code in (200, 201):
                customer = r.json()

                # Sync identity to central auth-service.
                try:
                    r_auth = requests.post(
                        f"{AUTH_SERVICE_URL}/auth/register/",
                        json={
                            "email": data["email"],
                            "password": data["password"],
                            "role": "customer",
                        },
                        timeout=3,
                    )
                    if r_auth.status_code in (200, 201):
                        request.session["access_token"] = r_auth.json().get("access", "")
                except Exception:
                    pass

                # Log them in automatically
                request.session["customer_id"] = customer["id"]
                request.session["customer_name"] = customer["name"]
                messages.success(request, f"Đăng ký thành công! Xin chào, {customer['name']}!")
                return redirect("store_home")
            else:
                resp = r.json()
                if "email" in resp:
                    messages.error(request, "Email này đã được đăng ký.")
                else:
                    messages.error(request, f"Lỗi: {resp}")
        except Exception as e:
            messages.error(request, f"Lỗi kết nối: {e}")
    return render(request, "store_register.html", {"customer": None})


def store_profile(request):
    customer = _get_store_customer(request)
    if not customer:
        return redirect("store_login")
    
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "phone": request.POST.get("phone"),
            "job_id": request.POST.get("job_id"),
        }
        try:
            r = requests.patch(f"{CUSTOMER_SERVICE_URL}/customers/{customer['id']}/", json=data, timeout=3)
            if r.status_code == 200:
                messages.success(request, "Cập nhật hồ sơ thành công!")
                request.session["customer_name"] = data["name"] # Sync name in session
            else:
                messages.error(request, f"Lỗi: {r.text}")
        except Exception as e:
            messages.error(request, f"Lỗi kết nối: {e}")
        return redirect("store_profile")

    # Fetch customer full info and available jobs
    full_info = {}
    jobs = []
    try:
        r_cust = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{customer['id']}/", timeout=3)
        if r_cust.status_code == 200:
            full_info = r_cust.json()
        
        r_jobs = requests.get(f"{CUSTOMER_SERVICE_URL}/jobs/", timeout=3)
        if r_jobs.status_code == 200:
            jobs = r_jobs.json()
    except Exception as e:
        messages.error(request, f"Lỗi lấy thông tin: {e}")

    return render(request, "store_profile.html", {
        "customer": full_info,
        "jobs": jobs,
    })


def store_logout(request):
    request.session.flush()
    messages.success(request, "Đã đăng xuất thành công.")
    return redirect("store_home")


def store_cart(request):
    customer = _get_store_customer(request)
    if not customer:
        messages.error(request, "Vui lòng đăng nhập để xem giỏ hàng.")
        return redirect("store_login")
    items = []
    cart_id = None
    error = None
    try:
        r = requests.get(f"{CART_SERVICE_URL}/carts/{customer['id']}/", timeout=3)
        data = r.json()
        if isinstance(data, dict) and "cart_id" in data:
            cart_id = data["cart_id"]
            items = data.get("items", [])
        elif isinstance(data, dict) and "error" in data:
            error = data["error"]
    except Exception as e:
        error = str(e)
        
    # Cache product lookups per (type, id) across iteration
    product_cache = {}
    total = 0
    enriched = []
    for item in items:
        ptype = item.get("product_type", "book")
        pid = item.get("product_id", item.get("book_id"))
        entry = PRODUCT_SERVICE_MAP.get(ptype)
        product = {"name": f"{ptype} #{pid}", "price": 0}
        if entry:
            base_url, plural = entry
            key = (ptype, pid)
            if key in product_cache:
                product = product_cache[key]
            else:
                try:
                    rp = requests.get(f"{base_url}/{plural}/{pid}/", timeout=3)
                    if rp.status_code == 200:
                        product = rp.json()
                except Exception:
                    pass
                product_cache[key] = product
        title = product.get("title") or product.get("name") or f"{ptype} #{pid}"
        author = product.get("author") or product.get("brand") or product.get("category") or ""
        price = float(product.get("price", 0) or 0)
        subtotal = price * item["quantity"]
        total += subtotal
        enriched.append({
            **item,
            "product_id": pid,
            "product_type": ptype,
            "product_label": _get_product_label(ptype),
            "detail_url": _build_store_product_detail_url(ptype, pid),
            "book": {"title": title, "author": author, "price": price},
            "item_title": title,
            "item_subtitle": author,
            "subtotal": subtotal,
        })
            
    return render(request, "store_cart.html", {
        "items": enriched, "cart_id": cart_id,
        "total": total, "error": error, "customer": customer,
    })


def store_add_to_cart(request):
    if request.method != "POST":
        return redirect("store_home")

    next_url = request.POST.get("next", "/store/")
    if not next_url.startswith("/store"):
        next_url = "/store/"

    customer = _get_store_customer(request)
    if not customer:
        messages.error(request, "Vui lòng đăng nhập để thêm vào giỏ hàng.")
        return redirect("store_login")

    book_id = request.POST.get("book_id")
    clothe_id = request.POST.get("clothe_id")
    
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1
    quantity = max(1, min(quantity, 99))

    cart_id = _get_cart_id(customer["id"])
    if not cart_id:
        messages.error(request, "Không tìm thấy giỏ hàng.")
        return redirect(next_url)

    if book_id and book_id != "None" and book_id != "":
        try:
            r_book = requests.get(f"{BOOK_SERVICE_URL}/books/{int(book_id)}/", timeout=3)
            if r_book.status_code == 200:
                book = r_book.json()
                if int(book.get("stock", 0) or 0) <= 0:
                    messages.error(request, f"Sách '{book.get('title', '')}' đã hết hàng.")
                    return redirect(next_url)
            else:
                messages.error(request, "Không thể kiểm tra tồn kho hiện tại.")
                return redirect(next_url)
        except Exception as e:
            messages.error(request, f"Lỗi kết nối kiểm tra tồn kho: {e}")
            return redirect(next_url)
            
        try:
            r = requests.post(f"{CART_SERVICE_URL}/cart-items/", json={
                "cart": cart_id,
                "product_id": int(book_id),
                "product_type": "book",
                "quantity": quantity,
            }, timeout=3)
            if r.status_code in (200, 201):
                publish_event('add_to_cart', customer['id'], product_type='book',
                              product_id=int(book_id), weight=quantity)
                messages.success(request, "Đã thêm Sách vào giỏ hàng!")
            else:
                messages.error(request, f"Lỗi thêm vào giỏ: {r.text}")
        except Exception as e:
            messages.error(request, f"Lỗi kết nối giỏ hàng: {e}")
            
    elif clothe_id and clothe_id != "None" and clothe_id != "":
        try:
            r_clothe = requests.get(f"{CLOTHE_SERVICE_URL}/clothes/{int(clothe_id)}/", timeout=3)
            if r_clothe.status_code == 200:
                clothe = r_clothe.json()
                if int(clothe.get("stock", 0) or 0) <= 0:
                    messages.error(request, f"Sản phẩm '{clothe.get('name', '')}' đã hết hàng.")
                    return redirect(next_url)
            else:
                messages.error(request, "Không thể kiểm tra tồn kho hiện tại.")
                return redirect(next_url)
        except Exception as e:
            messages.error(request, f"Lỗi kết nối kiểm tra tồn kho: {e}")
            return redirect(next_url)
            
        try:
            r = requests.post(f"{CART_SERVICE_URL}/cart-items/", json={
                "cart": cart_id,
                "product_id": int(clothe_id),
                "product_type": "clothe",
                "quantity": quantity,
            }, timeout=3)
            if r.status_code in (200, 201):
                publish_event('add_to_cart', customer['id'], product_type='clothe',
                              product_id=int(clothe_id), weight=quantity)
                messages.success(request, "Đã thêm Quần áo vào giỏ hàng!")
            else:
                messages.error(request, f"Lỗi thêm vào giỏ: {r.text}")
        except Exception as e:
            messages.error(request, f"Lỗi kết nối giỏ hàng: {e}")
    else:
        # Generic product types mới (electronic, food, ...): client gửi product_id + product_type
        generic_pid = request.POST.get("product_id")
        generic_ptype = request.POST.get("product_type")
        if generic_pid and generic_ptype and generic_ptype in PRODUCT_SERVICE_MAP:
            base_url, plural = PRODUCT_SERVICE_MAP[generic_ptype]
            try:
                r_product = requests.get(f"{base_url}/{plural}/{int(generic_pid)}/", timeout=3)
                if r_product.status_code == 200:
                    product = r_product.json()
                    if int(product.get("stock", 0) or 0) <= 0:
                        messages.error(request, f"Sản phẩm '{product.get('name') or product.get('title') or generic_ptype}' đã hết hàng.")
                        return redirect(next_url)
                else:
                    messages.error(request, "Không thể kiểm tra tồn kho hiện tại.")
                    return redirect(next_url)
            except Exception as e:
                messages.error(request, f"Lỗi kết nối kiểm tra tồn kho: {e}")
                return redirect(next_url)
            try:
                r = requests.post(f"{CART_SERVICE_URL}/cart-items/", json={
                    "cart": cart_id,
                    "product_id": int(generic_pid),
                    "product_type": generic_ptype,
                    "quantity": quantity,
                }, timeout=3)
                if r.status_code in (200, 201):
                    publish_event('add_to_cart', customer['id'],
                                  product_type=generic_ptype,
                                  product_id=int(generic_pid), weight=quantity)
                    messages.success(request, "Đã thêm sản phẩm vào giỏ hàng!")
                else:
                    messages.error(request, f"Lỗi thêm vào giỏ: {r.text}")
            except Exception as e:
                messages.error(request, f"Lỗi kết nối giỏ hàng: {e}")
        else:
            messages.error(request, "Dữ liệu sản phẩm không hợp lệ.")

    return redirect(next_url)


def store_book_detail(request, book_id):
    book = None
    reviews_data = {"reviews": [], "average_rating": 0, "total_reviews": 0}
    # Behavior event: view
    customer = _get_store_customer(request)
    if customer:
        publish_event('view', customer['id'], product_type='book', product_id=book_id)
    try:
        # Fetch single book directly from book-service
        r = requests.get(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=3)
        if r.status_code == 200:
            book = r.json()
    except Exception as e:
        print(f"Error fetching book detail: {e}")
    
    try:
        r = requests.get(f"{COMMENT_RATE_SERVICE_URL}/reviews/book/{book_id}/", timeout=3)
        if r.status_code == 200:
            reviews_data = r.json()
    except Exception:
        pass
    
    return render(request, "store_book_detail.html", {
        "book": book,
        "customer": _get_store_customer(request),
        "reviews": reviews_data.get("reviews", []),
        "average_rating": reviews_data.get("average_rating", 0),
        "total_reviews": reviews_data.get("total_reviews", 0),
    })


def store_remove_from_cart(request, product_type, product_id):
    customer = _get_store_customer(request)
    if not customer:
        return redirect("store_login")
    cart_id = _get_cart_id(customer["id"])
    if cart_id:
        try:
            requests.delete(
                f"{CART_SERVICE_URL}/cart-items/{cart_id}/{product_type}/{product_id}/",
                timeout=3,
            )
            publish_event('remove_from_cart', customer['id'],
                          product_type=product_type, product_id=product_id)
            messages.success(request, "Đã xóa sản phẩm khỏi giỏ hàng.")
        except Exception as e:
            messages.error(request, f"Lỗi: {e}")
    return redirect("store_cart")


def store_checkout(request):
    customer = _get_store_customer(request)
    if not customer:
        return redirect("store_login")
    
    if request.method != "POST":
        return redirect("store_cart")

    # 1. Get cart items
    try:
        r_cart = requests.get(f"{CART_SERVICE_URL}/carts/{customer['id']}/", timeout=3)
        cart_data = r_cart.json()
        raw_items = cart_data.get("items", [])
    except Exception as e:
        messages.error(request, f"Lỗi lấy thông tin giỏ hàng: {e}")
        return redirect("store_cart")

    if not raw_items:
        messages.error(request, "Giỏ hàng trống.")
        return redirect("store_home")

    # 2. Pre-check stock và gom giá — map product_type -> service
    items_to_order = []
    total_price = 0
    try:
        for ri in raw_items:
            ptype = ri.get("product_type", "book")
            pid = ri.get("product_id", ri.get("book_id"))
            entry = PRODUCT_SERVICE_MAP.get(ptype)
            if not entry:
                messages.error(request, f"Loại sản phẩm '{ptype}' không hỗ trợ.")
                return redirect("store_cart")
            base_url, plural = entry
            r = requests.get(f"{base_url}/{plural}/{pid}/", timeout=3)
            if r.status_code != 200:
                messages.error(request, f"Sản phẩm {ptype}#{pid} không tồn tại.")
                return redirect("store_cart")
            prod = r.json()
            title = prod.get("title") or prod.get("name") or f"{ptype}#{pid}"
            if int(prod.get("stock", 0) or 0) < ri["quantity"]:
                messages.error(request, f"'{title}' không đủ hàng (Còn lại: {prod.get('stock', 0)}).")
                return redirect("store_cart")
            price = float(prod.get("price", 0))
            items_to_order.append({
                "product_id": pid,
                "product_type": ptype,
                "quantity": ri["quantity"],
                "price": price,
                "title": title,
            })
            total_price += price * ri["quantity"]
    except Exception as e:
        messages.error(request, f"Lỗi kiểm tra kho: {e}")
        return redirect("store_cart")

    # 3. Reduce stock — dùng PRODUCT_SERVICE_MAP
    reduced_items = []
    stock_failed = False
    for item in items_to_order:
        base_url, plural = PRODUCT_SERVICE_MAP[item["product_type"]]
        try:
            res = requests.post(
                f"{base_url}/{plural}/{item['product_id']}/reduce-stock/",
                json={"quantity": item["quantity"]}, timeout=3,
            )
            if res.status_code == 200:
                reduced_items.append(item)
            else:
                stock_failed = True
                error_msg = res.json().get("error", "Lỗi không xác định")
                messages.error(request, f"Không thể trừ kho cho '{item['title']}': {error_msg}")
                break
        except Exception as e:
            stock_failed = True
            messages.error(request, f"Lỗi kết nối khi trừ kho: {e}")
            break

    if stock_failed:
        # Rollback
        for ri in reduced_items:
            try:
                base_url, plural = PRODUCT_SERVICE_MAP[ri["product_type"]]
                requests.post(
                    f"{base_url}/{plural}/{ri['product_id']}/restore-stock/",
                    json={"quantity": ri["quantity"]}, timeout=3,
                )
            except Exception:
                pass
        return redirect("store_cart")

    # 4. Create the Order
    province = request.POST.get("province", "Khác")
    address_detail = request.POST.get("address_detail", "")
    full_address = f"{address_detail}, {province}"
    payment_method = request.POST.get("payment_method", "cod")
    
    shipping_fee = 0
    if province not in ["Hà Nội", "Hồ Chí Minh"]:
        shipping_fee = 30000
    
    order_data = {
        "customer_id": customer["id"],
        "total_price": total_price,
        "shipping_fee": shipping_fee,
        "shipping_address": full_address,
        "payment_method": payment_method,
        "items": [
            {
                "product_id": i["product_id"],
                "product_type": i["product_type"],
                "quantity": i["quantity"],
                "price": i["price"],
            } for i in items_to_order
        ]
    }
    
    try:
        r_order = requests.post(f"{ORDER_SERVICE_URL}/orders/", json=order_data, timeout=5)
        if r_order.status_code == 201:
            order_resp = r_order.json()

            # Behavior event: purchase (publish per item)
            for it in items_to_order:
                publish_event('purchase', customer['id'],
                              product_type=it['product_type'],
                              product_id=it['product_id'], weight=it['quantity'])

            # 5. Clear cart
            try:
                requests.delete(f"{CART_SERVICE_URL}/carts/{customer['id']}/clear/", timeout=3)
            except Exception:
                pass
            
            # 6. VNPay Simulation
            if payment_method == 'vnpay':
                try:
                    pay_res = requests.post(f"{PAY_SERVICE_URL}/payments/", json={
                        "order_id": order_resp.get("id"),
                        "customer_id": customer["id"],
                        "amount": order_resp.get("grand_total"),
                        "method": "vnpay",
                    }, timeout=3)
                    if pay_res.status_code == 201:
                        pay_data = pay_res.json()
                        return render(request, "store_vnpay_sim.html", {
                            "order": order_resp,
                            "payment": pay_data
                        })
                except Exception:
                    pass

            messages.success(request, "Đặt hàng thành công! Hệ thống Saga đang xử lý đơn hàng của bạn.")
            return render(request, "store_success.html", {"customer": customer, "order": order_resp})

        else:
            # Rollback
            for ri in reduced_items:
                try:
                    base_url, plural = PRODUCT_SERVICE_MAP[ri["product_type"]]
                    requests.post(
                        f"{base_url}/{plural}/{ri['product_id']}/restore-stock/",
                        json={"quantity": ri["quantity"]}, timeout=3,
                    )
                except Exception:
                    pass
            messages.error(request, f"Lỗi tạo đơn hàng: {r_order.text}")
    except Exception as e:
        for ri in reduced_items:
            try:
                base_url, plural = PRODUCT_SERVICE_MAP[ri["product_type"]]
                requests.post(
                    f"{base_url}/{plural}/{ri['product_id']}/restore-stock/",
                    json={"quantity": ri["quantity"]}, timeout=3,
                )
            except Exception:
                pass
        messages.error(request, f"Lỗi kết nối order-service: {e}")
    
    return redirect("store_cart")


def store_orders(request):
    customer = _get_store_customer(request)
    if not customer:
        messages.error(request, "Vui lòng đăng nhập để xem đơn hàng.")
        return redirect("store_login")
    orders = []
    try:
        r = requests.get(f"{ORDER_SERVICE_URL}/orders/customer/{customer['id']}/", timeout=5)
        orders = r.json()
        if not isinstance(orders, list):
            orders = []
    except Exception:
        pass
    return render(request, "store_orders.html", {
        "orders": orders,
        "customer": customer,
    })


def store_order_detail(request, order_id):
    customer = _get_store_customer(request)
    if not customer:
        return redirect("store_login")
    order = None
    shipment = None
    payment = None
    try:
        r = requests.get(f"{ORDER_SERVICE_URL}/orders/{order_id}/", timeout=5)
        if r.status_code == 200:
            order = r.json()
            if order.get("customer_id") != customer["id"]:
                messages.error(request, "Bạn không có quyền xem đơn hàng này.")
                return redirect("store_orders")
            # Enrich items theo product_type
            _enrich_order_items(order.get("items", []))
            # Get shipment info
            try:
                r_ship = requests.get(f"{SHIP_SERVICE_URL}/shipments/order/{order_id}/", timeout=3)
                if r_ship.status_code == 200:
                    shipment = r_ship.json()
            except Exception:
                pass
            # Get payment info
            try:
                r_pay = requests.get(f"{PAY_SERVICE_URL}/payments/order/{order_id}/", timeout=3)
                if r_pay.status_code == 200:
                    pay_data = r_pay.json()
                    if isinstance(pay_data, list) and pay_data:
                        payment = pay_data[0]
            except Exception:
                pass
    except Exception:
        pass
    return render(request, "store_order_detail.html", {
        "order": order,
        "customer": customer,
        "shipment": shipment,
        "payment": payment,
    })


def store_cancel_order(request, order_id):
    customer = _get_store_customer(request)
    if not customer:
        return redirect("store_login")
    
    if request.method == "POST":
        try:
            # Gửi yêu cầu DELETE sang order-service để hủy đơn và hoàn kho
            r = requests.delete(f"{ORDER_SERVICE_URL}/orders/{order_id}/", timeout=5)
            if r.status_code == 200:
                messages.success(request, "Đã hủy đơn hàng thành công và hệ thống đang hoàn lại sách vào kho.")
            else:
                resp = r.json()
                error_msg = resp.get("error", "Không thể hủy đơn hàng lúc này.")
                messages.error(request, f"Lỗi: {error_msg}")
        except Exception as e:
            messages.error(request, f"Lỗi kết nối khi hủy đơn: {e}")
            
    return redirect("store_order_detail", order_id=order_id)

def store_payment_simulate(request, order_id):
    customer = _get_store_customer(request)
    if not customer:
        return redirect("store_login")
    
    try:
        # 1. Get transaction info from pay-service
        r_pay_list = requests.get(f"{PAY_SERVICE_URL}/payments/order/{order_id}/", timeout=3)
        if r_pay_list.status_code == 200:
            payments = r_pay_list.json()
            if payments:
                pay = payments[0]
                # 2. CALL THE NEW SECURE WEBHOOK (Production approach)
                requests.post(f"{PAY_SERVICE_URL}/payments/confirm-payment/", 
                               json={
                                   "order_id": order_id,
                                   "transaction_id": pay["transaction_id"],
                                   "secure_token": "SECRET_PAYMENT_TOKEN" # In real life, this is a calculated signature
                               }, timeout=3)
                
                messages.success(request, "Thanh toán thành công! Hệ thống đang xử lý vận chuyển.")
            else:
                messages.error(request, "Không tìm thấy thông tin thanh toán cho đơn hàng này.")
        else:
            messages.error(request, "Lỗi kết nối tới dịch vụ thanh toán.")
    except Exception as e:
        messages.error(request, f"Lỗi xử lý thanh toán: {e}")
    
    return redirect("store_order_detail", order_id=order_id)


def store_confirm_receipt(request, order_id):
    customer = _get_store_customer(request)
    if not customer:
        return redirect("store_login")
    
    try:
        # 1. Update order status to delivered
        requests.patch(f"{ORDER_SERVICE_URL}/orders/{order_id}/", 
                       json={"status": "delivered"}, timeout=5)
        
        # 2. Update shipment status to delivered
        r_ship = requests.get(f"{SHIP_SERVICE_URL}/shipments/order/{order_id}/", timeout=3)
        if r_ship.status_code == 200:
            shipment = r_ship.json()
            ship_id = shipment["id"]
            requests.patch(f"{SHIP_SERVICE_URL}/shipments/{ship_id}/", 
                           json={"status": "delivered"}, timeout=3)
        
        messages.success(request, "Xác nhận nhận hàng thành công. Bạn có thể để lại đánh giá cho sản phẩm.")
    except Exception as e:
        messages.error(request, f"Lỗi xác nhận: {e}")
    
    return redirect("store_order_detail", order_id=order_id)


# ── ADMIN ORDER VIEWS ────────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_order_list(request):
    orders = []
    customers_map = {}
    try:
        r = requests.get(f"{ORDER_SERVICE_URL}/orders/", timeout=5)
        orders = r.json()
        if not isinstance(orders, list):
            orders = []
    except Exception:
        pass
    try:
        customers = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=3).json()
        if isinstance(customers, list):
            customers_map = {c["id"]: c for c in customers}
    except Exception:
        pass
    for order in orders:
        cust = customers_map.get(order.get("customer_id"), {})
        order["customer_name"] = cust.get("name", f"KH #{order.get('customer_id')}")
        order["customer_email"] = cust.get("email", "")
    return render(request, "orders.html", {"orders": orders})


@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_order_detail(request, order_id):
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status:
            try:
                requests.patch(f"{ORDER_SERVICE_URL}/orders/{order_id}/",
                               json={"status": new_status}, timeout=5)
                messages.success(request, f"Đã cập nhật trạng thái đơn hàng #{order_id}.")
            except Exception as e:
                messages.error(request, f"Lỗi: {e}")
        return redirect("admin_order_detail", order_id=order_id)

    order = None
    try:
        r = requests.get(f"{ORDER_SERVICE_URL}/orders/{order_id}/", timeout=5)
        if r.status_code == 200:
            order = r.json()
            # Customer info
            try:
                customers = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=3).json()
                cust = next((c for c in customers if c["id"] == order.get("customer_id")), {})
                order["customer_name"] = cust.get("name", f"KH #{order.get('customer_id')}")
                order["customer_email"] = cust.get("email", "")
            except Exception:
                order["customer_name"] = f"KH #{order.get('customer_id')}"
                order["customer_email"] = ""
            _enrich_order_items(order.get("items", []))
    except Exception:
        pass
    return render(request, "order_detail.html", {"order": order})


# ── ADMIN STAFF VIEWS ─────────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_staff_list(request):
    error = None
    staff = []
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "email": request.POST.get("email"),
            "phone": request.POST.get("phone", ""),
            "role": request.POST.get("role", "sales"),
        }
        try:
            r = requests.post(f"{STAFF_SERVICE_URL}/staff/", json=data, timeout=3)
            if r.status_code in (200, 201):
                messages.success(request, "Thêm nhân viên thành công!")
            else:
                messages.error(request, f"Lỗi: {r.text}")
        except Exception as e:
            messages.error(request, f"Không kết nối được staff-service: {e}")
        return redirect("admin_staff_list")
    try:
        r = requests.get(f"{STAFF_SERVICE_URL}/staff/", timeout=3)
        staff = r.json()
        if not isinstance(staff, list):
            staff = []
    except Exception as e:
        error = str(e)
    return render(request, "staff.html", {"staff": staff, "error": error})


# ── ADMIN MANAGER VIEWS ──────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_manager_list(request):
    error = None
    managers = []
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "email": request.POST.get("email"),
            "phone": request.POST.get("phone", ""),
            "department": request.POST.get("department", "general"),
        }
        try:
            r = requests.post(f"{MANAGER_SERVICE_URL}/managers/", json=data, timeout=3)
            if r.status_code in (200, 201):
                messages.success(request, "Thêm quản lý thành công!")
            else:
                messages.error(request, f"Lỗi: {r.text}")
        except Exception as e:
            messages.error(request, f"Không kết nối được manager-service: {e}")
        return redirect("admin_manager_list")
    try:
        r = requests.get(f"{MANAGER_SERVICE_URL}/managers/", timeout=3)
        managers = r.json()
        if not isinstance(managers, list):
            managers = []
    except Exception as e:
        error = str(e)
    return render(request, "managers.html", {"managers": managers, "error": error})


# ── ADMIN CATALOG VIEWS ──────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_catalog_list(request):
    error = None
    categories = []
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "description": request.POST.get("description", ""),
        }
        try:
            r = requests.post(f"{CATALOG_SERVICE_URL}/categories/", json=data, timeout=3)
            if r.status_code in (200, 201):
                messages.success(request, "Thêm danh mục thành công!")
            else:
                messages.error(request, f"Lỗi: {r.text}")
        except Exception as e:
            messages.error(request, f"Không kết nối được catalog-service: {e}")
        return redirect("admin_catalog_list")
    try:
        r = requests.get(f"{CATALOG_SERVICE_URL}/categories/", timeout=3)
        categories = r.json()
        if not isinstance(categories, list):
            categories = []
    except Exception as e:
        error = str(e)
    return render(request, "catalog.html", {"categories": categories, "error": error})


# ── ADMIN PAYMENT VIEWS ──────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_payment_list(request):
    payments = []
    try:
        r = requests.get(f"{PAY_SERVICE_URL}/payments/", timeout=5)
        payments = r.json()
        if not isinstance(payments, list):
            payments = []
    except Exception:
        pass
    return render(request, "payments.html", {"payments": payments})


# ── ADMIN SHIPMENT VIEWS ─────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_shipment_list(request):
    shipments = []
    try:
        r = requests.get(f"{SHIP_SERVICE_URL}/shipments/", timeout=5)
        shipments = r.json()
        if not isinstance(shipments, list):
            shipments = []
    except Exception:
        pass
    return render(request, "shipments.html", {"shipments": shipments})


# ── ADMIN REVIEW VIEWS ───────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_review_list(request):
    reviews = []
    try:
        r = requests.get(f"{COMMENT_RATE_SERVICE_URL}/reviews/", timeout=5)
        reviews = r.json()
        if not isinstance(reviews, list):
            reviews = []
    except Exception:
        pass
    return render(request, "reviews.html", {"reviews": reviews})


# ── STORE REVIEW VIEWS ───────────────────────────────────────

def store_add_review(request, book_id):
    customer = _get_store_customer(request)
    if not customer:
        messages.error(request, "Vui lòng đăng nhập để đánh giá.")
        return redirect("store_login")
    
    # Check if customer has bought this book and order is delivered
    has_purchased = False
    try:
        r_orders = requests.get(f"{ORDER_SERVICE_URL}/orders/customer/{customer['id']}/", timeout=5)
        if r_orders.status_code == 200:
            orders = r_orders.json()
            for order in orders:
                if order.get("status") == "delivered":
                    for item in order.get("items", []):
                        if item.get("product_type", "book") == "book" and item.get("product_id", item.get("book_id")) == book_id:
                            has_purchased = True
                            break
                if has_purchased: break
    except Exception:
        pass
    
    if not has_purchased:
        messages.error(request, "Bạn chỉ có thể đánh giá sách sau khi đã nhận hàng thành công.")
        return redirect("store_book_detail", book_id=book_id)

    if request.method == "POST":
        data = {
            "customer_id": customer["id"],
            "book_id": book_id,
            "rating": int(request.POST.get("rating", 5)),
            "comment": request.POST.get("comment", ""),
        }
        try:
            r = requests.post(f"{COMMENT_RATE_SERVICE_URL}/reviews/", json=data, timeout=3)
            if r.status_code in (200, 201):
                messages.success(request, "Đánh giá thành công!")
            else:
                resp = r.json()
                if "unique" in str(resp).lower() or "unique_together" in str(resp).lower():
                    messages.error(request, "Bạn đã đánh giá sách này rồi.")
                else:
                    messages.error(request, f"Lỗi: {resp}")
        except Exception as e:
            messages.error(request, f"Lỗi kết nối: {e}")
    return redirect("store_book_detail", book_id=book_id)


def api_secure_echo(request):
    return JsonResponse({
        "status": "ok",
        "message": "Gateway token validation passed",
    })


# ── CLOTHE VIEWS ─────────────────────────────────────────────

@user_passes_test(is_staff_check, login_url='/admin/login/')
def admin_clothe_list(request):
    error = None
    clothes = []
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "material": request.POST.get("material"),
            "price": request.POST.get("price"),
            "stock": request.POST.get("stock"),
        }
        try:
            r = requests.post(f"{CLOTHE_SERVICE_URL}/clothes/", json=data, timeout=3)
            if r.status_code in (200, 201):
                messages.success(request, "Thêm quần áo thành công!")
            else:
                messages.error(request, f"Lỗi: {r.text}")
        except Exception as e:
            messages.error(request, f"Lỗi kết nối: {e}")
        return redirect("admin_clothe_list")
        
    try:
        r = requests.get(f"{CLOTHE_SERVICE_URL}/clothes/", timeout=3)
        clothes = r.json()
    except Exception as e:
        error = str(e)
    return render(request, "clothes.html", {"clothes": clothes, "error": error})

def store_clothes(request):
    clothes = []
    try:
        r = requests.get(f"{CLOTHE_SERVICE_URL}/clothes/", timeout=3)
        clothes = r.json()
    except Exception:
        pass
    
    customer = _get_store_customer(request)
    return render(request, "store_clothes.html", {"clothes": clothes, "customer": customer})

def store_clothe_detail(request, clothe_id):
    clothe = None
    customer = _get_store_customer(request)
    if customer:
        publish_event('view', customer['id'], product_type='clothe', product_id=clothe_id)
    try:
        r = requests.get(f"{CLOTHE_SERVICE_URL}/clothes/{clothe_id}/", timeout=3)
        if r.status_code == 200:
            clothe = r.json()
    except Exception:
        pass
    return render(request, "store_clothe_detail.html", {"clothe": clothe, "customer": customer})


def store_product_list(request, product_type):
    if product_type in ("book", "clothe"):
        return redirect("store_home" if product_type == "book" else "store_clothes")
    entry = PRODUCT_SERVICE_MAP.get(product_type)
    if not entry:
        messages.error(request, "Danh mục sản phẩm không tồn tại.")
        return redirect("store_home")

    base_url, plural = entry
    products = []
    customer = _get_store_customer(request)
    error = None
    try:
        r = requests.get(f"{base_url}/{plural}/", timeout=4)
        if r.status_code == 200:
            products = r.json()
        else:
            error = f"Khong the tai du lieu tu {product_type}-service."
    except Exception as e:
        error = str(e)

    if not isinstance(products, list):
        products = []
    for p in products:
        p["detail_url"] = _build_store_product_detail_url(product_type, p.get("id"))

    return render(request, "store_product_list.html", {
        "customer": customer,
        "products": products,
        "product_type": product_type,
        "product_label": _get_product_label(product_type),
        "error": error,
    })


def store_product_detail(request, product_type, product_id):
    if product_type == "book":
        return redirect("store_book_detail", book_id=product_id)
    if product_type == "clothe":
        return redirect("store_clothe_detail", clothe_id=product_id)
    entry = PRODUCT_SERVICE_MAP.get(product_type)
    if not entry:
        messages.error(request, "San pham khong ton tai.")
        return redirect("store_home")

    base_url, plural = entry
    product = None
    customer = _get_store_customer(request)
    if customer:
        publish_event('view', customer['id'], product_type=product_type, product_id=product_id)
    try:
        r = requests.get(f"{base_url}/{plural}/{product_id}/", timeout=4)
        if r.status_code == 200:
            product = r.json()
    except Exception:
        pass

    subtitle_key = PRODUCT_TYPE_META.get(product_type, {}).get("subtitle_key", "")
    subtitle_value = product.get(subtitle_key, "") if isinstance(product, dict) else ""
    return render(request, "store_product_detail.html", {
        "customer": customer,
        "product": product,
        "product_type": product_type,
        "product_id": product_id,
        "product_label": _get_product_label(product_type),
        "subtitle_key": subtitle_key,
        "subtitle_value": subtitle_value,
    })


# ============================================================
#  AI CHATBOT PROXY
# ============================================================
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json as json_module

@csrf_exempt
def ai_chat_proxy(request):
    """
    Proxy chuyển tiếp request chat từ frontend → recommender-ai-service.
    Đặt tại api-gateway để tránh CORS và ẩn địa chỉ nội bộ.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        body = json_module.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = body.get("message", "").strip()
    if not message:
        return JsonResponse({"error": "Thiếu nội dung tin nhắn"}, status=400)

    customer_id = request.session.get("customer_id")
    # Publish search event cho analytics/GraphRAG
    if customer_id:
        publish_event('search', customer_id, query=message, routing_key='search')

    ai_url = os.environ.get('AI_SERVICE_URL', 'http://ai-service:8000')
    try:
        resp = requests.post(
            f"{ai_url}/chat/",
            json={"message": message, "user_id": customer_id},
            timeout=30,
        )
        return JsonResponse(resp.json(), status=resp.status_code,
                            json_dumps_params={'ensure_ascii': False})
    except requests.Timeout:
        return JsonResponse({"error": "AI service đang bận, thử lại sau."},
                            status=503, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500,
                            json_dumps_params={'ensure_ascii': False})
