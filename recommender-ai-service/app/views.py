import os
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings

from .ai.ncf_model import ncf_trainer
from .ai.knowledge_base import knowledge_base
from .ai.rag_chat import chatbot


# ============================================================
#  HELPER: Lấy dữ liệu từ các microservices khác
# ============================================================

def fetch_json(url, timeout=5):
    """Gọi HTTP GET, trả về JSON hoặc None nếu lỗi."""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def fetch_all_books():
    return fetch_json(f"{settings.BOOK_SERVICE_URL}/books/") or []


def fetch_all_clothes():
    return fetch_json(f"{settings.CLOTHE_SERVICE_URL}/clothes/") or []


def fetch_customer_orders(customer_id):
    return fetch_json(f"{settings.ORDER_SERVICE_URL}/orders/customer/{customer_id}/") or []


def fetch_all_reviews():
    return fetch_json(f"{settings.COMMENT_RATE_SERVICE_URL}/reviews/") or []


def fetch_book_reviews(book_id):
    return fetch_json(f"{settings.COMMENT_RATE_SERVICE_URL}/reviews/book/{book_id}/") or {}


# ============================================================
#  1. RULE-BASED RECOMMENDATION (giữ lại từ phiên bản cũ)
# ============================================================

class RecommendForCustomer(APIView):
    """Gợi ý theo rule (job title/industry) - phiên bản cũ."""

    def get(self, request, customer_id):
        try:
            customer_profile = fetch_json(
                f"{settings.CUSTOMER_SERVICE_URL}/customers/{customer_id}/"
            ) or {}

            job_title = customer_profile.get("job_info", {}).get("title", "").lower()
            industry = customer_profile.get("job_info", {}).get("industry", "").lower()

            ordered_book_ids = set()
            for order in fetch_customer_orders(customer_id):
                for item in order.get('items', []):
                    ordered_book_ids.add(item.get('book_id'))

            all_books = fetch_all_books()
            scored = []
            for book in all_books:
                if book.get('id') in ordered_book_ids:
                    continue
                score = 0
                title = book.get("title", "").lower()
                if "engineer" in job_title or "it" in industry:
                    if any(x in title for x in ["code", "java", "python", "system", "data", "algorithm"]):
                        score += 50
                if "doctor" in job_title or "medical" in industry:
                    if any(x in title for x in ["health", "medical", "anatomy"]):
                        score += 50
                if "student" in job_title:
                    if any(x in title for x in ["study", "guide", "learn"]):
                        score += 30
                reviews = fetch_book_reviews(book['id'])
                score += reviews.get('average_rating', 0) * 5
                scored.append((book, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            return Response({
                "customer_id": customer_id,
                "persona": job_title or "generic",
                "strategy": "rule_based",
                "recommendations": [b for b, _ in scored[:5]],
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class PopularBooks(APIView):
    """Sách phổ biến nhất theo đánh giá."""

    def get(self, request):
        try:
            all_books = fetch_all_books()
            scored = []
            for book in all_books:
                reviews = fetch_book_reviews(book['id'])
                scored.append({
                    **book,
                    'average_rating': reviews.get('average_rating', 0),
                    'total_reviews': reviews.get('total_reviews', 0),
                })
            scored.sort(key=lambda x: (x['average_rating'], x['total_reviews']), reverse=True)
            return Response(scored[:10])
        except Exception:
            return Response([], status=500)


# ============================================================
#  2. DEEP LEARNING - NCF RECOMMENDATION
# ============================================================

class TrainNCFModel(APIView):
    """
    POST /ai/train/
    Train mô hình NCF trên dữ liệu hiện tại.

    Luồng:
      1. Thu thập reviews từ comment-rate-service (explicit feedback)
      2. Thu thập orders (implicit feedback: đã mua = thích)
      3. Xây dựng tập tương tác user-item
      4. Train mô hình NCF và lưu ra disk
    """

    def post(self, request):
        try:
            all_reviews = fetch_all_reviews()
            all_books = fetch_all_books()
            all_clothes = fetch_all_clothes()

            # Tạo item_info: key = "book_<id>" hoặc "clothe_<id>"
            item_info = {}
            for book in all_books:
                key = f"book_{book['id']}"
                item_info[key] = {**book, "product_type": "book"}
            for clothe in all_clothes:
                key = f"clothe_{clothe['id']}"
                item_info[key] = {**clothe, "product_type": "clothe"}

            # Xây dựng interactions từ reviews (explicit feedback)
            interactions = []
            seen_customers = set()
            for review in all_reviews:
                customer_id = review.get('customer_id')
                book_id = review.get('book_id')
                rating = review.get('rating', 3)
                if customer_id and book_id:
                    interactions.append({
                        "user_id": int(customer_id),
                        "item_id": f"book_{book_id}",
                        "rating": float(rating),
                    })
                    seen_customers.add(int(customer_id))

            # Thêm implicit feedback từ orders nếu chưa đủ data
            if len(interactions) < 10:
                for cid in list(seen_customers)[:30]:
                    orders = fetch_customer_orders(cid)
                    for order in orders:
                        for item in order.get('items', []):
                            bid = item.get('book_id')
                            if bid:
                                interactions.append({
                                    "user_id": int(cid),
                                    "item_id": f"book_{bid}",
                                    "rating": 4.0,
                                })

            if len(interactions) < 5:
                return Response({
                    "error": "Chưa đủ dữ liệu để train.",
                    "current_interactions": len(interactions),
                    "tip": "Hãy thêm sản phẩm và tạo đơn hàng/đánh giá trước, sau đó gọi lại endpoint này.",
                }, status=400)

            epochs = int(request.data.get('epochs', 20))
            result = ncf_trainer.train(interactions, item_info, epochs=epochs)
            return Response(result)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class NCFRecommend(APIView):
    """
    GET /ai/recommend/<customer_id>/
    Gợi ý sản phẩm bằng mô hình NCF đã train.
    Tự động fallback sang rule-based nếu model chưa train.
    """

    def get(self, request, customer_id):
        ordered_ids = set()
        for order in fetch_customer_orders(customer_id):
            for item in order.get('items', []):
                bid = item.get('book_id')
                if bid:
                    ordered_ids.add(f"book_{bid}")

        recommendations, error = ncf_trainer.recommend(
            customer_id=int(customer_id),
            top_k=5,
            exclude_ids=ordered_ids,
        )

        if error:
            return Response({
                "customer_id": customer_id,
                "strategy": "model_not_ready",
                "message": error,
                "recommendations": [],
                "tip": "Gọi POST /ai/train/ để train mô hình trước.",
            })

        return Response({
            "customer_id": customer_id,
            "strategy": "ncf_deep_learning",
            "recommendations": recommendations,
        })


# ============================================================
#  3. KNOWLEDGE BASE MANAGEMENT
# ============================================================

class SyncKnowledgeBase(APIView):
    """
    POST /ai/knowledge/sync/
    Đồng bộ toàn bộ sản phẩm và chính sách vào Knowledge Base.
    Gọi endpoint này sau khi thêm sản phẩm mới hoặc thay đổi chính sách.
    """

    def post(self, request):
        try:
            all_books = fetch_all_books()
            all_clothes = fetch_all_clothes()

            product_result = knowledge_base.sync_products(all_books, all_clothes)
            policy_result = knowledge_base.seed_store_policies()
            faq_result = knowledge_base.seed_faq()
            stats = knowledge_base.get_stats()

            return Response({
                "status": "success",
                **product_result,
                **policy_result,
                **faq_result,
                "kb_stats": stats,
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class KnowledgeBaseStats(APIView):
    """GET /ai/knowledge/stats/ - Xem thống kê Knowledge Base."""

    def get(self, request):
        try:
            return Response({"collections": knowledge_base.get_stats()})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class KnowledgeSearch(APIView):
    """
    POST /ai/knowledge/search/
    Tìm kiếm ngữ nghĩa trong Knowledge Base.
    Body: {"query": "sách lập trình python", "n_results": 3}
    """

    def post(self, request):
        query = request.data.get('query', '').strip()
        if not query:
            return Response({"error": "Thiếu trường 'query'"}, status=400)
        n_results = int(request.data.get('n_results', 5))
        results = knowledge_base.search(query, n_results=n_results)
        return Response({"query": query, "results": results})


# ============================================================
#  4. RAG CHATBOT
# ============================================================

class ChatView(APIView):
    """
    POST /ai/chat/
    RAG Chatbot: trả lời câu hỏi khách hàng dựa trên Knowledge Base.

    Body:
    {
        "message": "Chính sách đổi trả như thế nào?",
        "customer_id": 1,
        "history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    """

    def post(self, request):
        message = request.data.get('message', '').strip()
        if not message:
            return Response({"error": "Thiếu trường 'message'"}, status=400)

        customer_id = request.data.get('customer_id')
        history = request.data.get('history', [])

        result = chatbot.chat(
            query=message,
            customer_id=customer_id,
            conversation_history=history,
        )
        return Response(result)


# ============================================================
#  5. DASHBOARD - Tổng quan AI system
# ============================================================

class AIDashboard(APIView):
    """GET /ai/ - Xem tổng quan trạng thái toàn bộ AI system."""

    def get(self, request):
        model_dir = os.environ.get('AI_MODEL_DIR', '/app/ai_models')
        model_exists = os.path.exists(os.path.join(model_dir, 'ncf_model.pt'))

        kb_stats = {}
        try:
            kb_stats = knowledge_base.get_stats()
        except Exception:
            pass

        services_status = {}
        for name, url in [
            ("book_service", f"{settings.BOOK_SERVICE_URL}/books/"),
            ("clothe_service", f"{settings.CLOTHE_SERVICE_URL}/clothes/"),
            ("order_service", f"{settings.ORDER_SERVICE_URL}/orders/"),
        ]:
            try:
                resp = requests.get(url, timeout=2)
                services_status[name] = "healthy" if resp.status_code == 200 else "error"
            except Exception:
                services_status[name] = "unreachable"

        return Response({
            "ai_components": {
                "ncf_model": {
                    "trained": model_exists,
                    "description": "Neural Collaborative Filtering - gợi ý sản phẩm bằng Deep Learning",
                    "train_endpoint": "POST /ai/train/",
                },
                "knowledge_base": {
                    "stats": kb_stats,
                    "description": "ChromaDB vector store - lưu kiến thức cửa hàng",
                    "sync_endpoint": "POST /ai/knowledge/sync/",
                },
                "rag_chatbot": {
                    "llm_enabled": chatbot.has_llm,
                    "mode": "claude_rag" if chatbot.has_llm else "extractive_rag",
                    "description": "RAG Chatbot - tư vấn khách hàng",
                    "chat_endpoint": "POST /ai/chat/",
                },
            },
            "microservices": services_status,
            "endpoints": {
                "GET  /ai/": "Dashboard tổng quan AI",
                "POST /ai/train/": "Train mô hình NCF Deep Learning",
                "GET  /ai/recommend/<id>/": "Gợi ý sản phẩm bằng AI",
                "POST /ai/knowledge/sync/": "Đồng bộ Knowledge Base từ sản phẩm",
                "GET  /ai/knowledge/stats/": "Thống kê Knowledge Base",
                "POST /ai/knowledge/search/": "Tìm kiếm ngữ nghĩa",
                "POST /ai/chat/": "Chat với AI tư vấn",
                "GET  /recommendations/<id>/": "Gợi ý theo rule-based (cũ)",
                "GET  /popular/": "Sản phẩm phổ biến nhất",
            },
        })
