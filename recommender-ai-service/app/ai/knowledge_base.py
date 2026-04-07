"""
Knowledge Base với ChromaDB
============================
Knowledge Base (KB) là kho lưu trữ kiến thức có cấu trúc.
Trong hệ thống này, KB chứa:
  - Thông tin sản phẩm (sách, quần áo)
  - Chính sách cửa hàng (vận chuyển, đổi trả)
  - FAQ (câu hỏi thường gặp)

ChromaDB là Vector Database:
  - Lưu văn bản dưới dạng VECTOR (mảng số thực)
  - Tìm kiếm theo NGỮ NGHĨA (semantic search), không phải từ khóa
  - Ví dụ: query "sách lập trình" sẽ tìm được "Python programming book"
    dù không có chữ "lập trình" trong tài liệu gốc

Sentence Transformers:
  - Mô hình AI chuyển văn bản → vector (embedding)
  - "all-MiniLM-L6-v2": mô hình nhỏ, nhanh, chất lượng tốt
  - 2 câu có nghĩa tương tự → 2 vector gần nhau trong không gian
"""

import os
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = os.environ.get('CHROMA_DB_DIR', '/app/chroma_db')

# Dùng sentence-transformers để tạo embeddings
# Model "all-MiniLM-L6-v2": chỉ 90MB, rất nhanh, phù hợp production nhỏ
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_chroma_client():
    """Khởi tạo ChromaDB client với persistent storage."""
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def get_embedding_function():
    """Trả về hàm embedding dùng sentence-transformers."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )


class KnowledgeBase:
    """
    Quản lý Knowledge Base cho hệ thống e-commerce.

    Collections (tương đương "bảng" trong CSDL thường):
      - "products": thông tin sản phẩm
      - "policies": chính sách cửa hàng
      - "faq": câu hỏi thường gặp
    """

    COLLECTIONS = ["products", "policies", "faq"]

    def __init__(self):
        self.client = get_chroma_client()
        self.ef = get_embedding_function()
        self._init_collections()

    def _init_collections(self):
        """Tạo các collections nếu chưa tồn tại."""
        self.collections = {}
        for name in self.COLLECTIONS:
            self.collections[name] = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.ef,
                metadata={"hnsw:space": "cosine"},  # dùng cosine similarity để đo khoảng cách
            )

    def sync_products(self, books, clothes):
        """
        Đồng bộ thông tin sản phẩm từ book-service và clothe-service vào KB.

        Mỗi sản phẩm được chuyển thành một "document" văn bản mô tả,
        sau đó được embed và lưu vào ChromaDB.
        """
        collection = self.collections["products"]

        documents = []
        metadatas = []
        ids = []

        # Xử lý sách
        for book in books:
            book_id = str(book.get('id', ''))
            title = book.get('title', 'Không có tiêu đề')
            author = book.get('author', 'Không rõ tác giả')
            price = book.get('price', 0)
            stock = book.get('stock', 0)
            description = book.get('description', '')

            # Tạo văn bản mô tả đầy đủ → sẽ được embed thành vector
            doc_text = (
                f"Sách: {title}. "
                f"Tác giả: {author}. "
                f"Giá: {price} VND. "
                f"Còn {stock} cuốn trong kho. "
                f"{description}"
            )

            documents.append(doc_text)
            metadatas.append({
                "type": "book",
                "product_id": book_id,
                "title": title,
                "author": author,
                "price": str(price),
                "stock": str(stock),
            })
            ids.append(f"book_{book_id}")

        # Xử lý quần áo
        for clothe in clothes:
            clothe_id = str(clothe.get('id', ''))
            name = clothe.get('name', 'Không có tên')
            material = clothe.get('material', '')
            price = clothe.get('price', 0)
            stock = clothe.get('stock', 0)

            doc_text = (
                f"Quần áo: {name}. "
                f"Chất liệu: {material}. "
                f"Giá: {price} VND. "
                f"Còn {stock} sản phẩm trong kho."
            )

            documents.append(doc_text)
            metadatas.append({
                "type": "clothe",
                "product_id": clothe_id,
                "name": name,
                "material": material,
                "price": str(price),
                "stock": str(stock),
            })
            ids.append(f"clothe_{clothe_id}")

        if documents:
            # upsert: thêm mới hoặc cập nhật nếu ID đã tồn tại
            collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

        return {"synced_books": len(books), "synced_clothes": len(clothes)}

    def seed_store_policies(self):
        """
        Thêm chính sách cửa hàng vào KB.
        Đây là "kiến thức nền" cho AI chatbot.
        """
        collection = self.collections["policies"]

        policies = [
            {
                "id": "shipping_policy",
                "text": (
                    "Chính sách vận chuyển: Giao hàng toàn quốc trong 2-5 ngày làm việc. "
                    "Miễn phí vận chuyển cho đơn hàng từ 300.000 VND trở lên. "
                    "Phí vận chuyển tiêu chuẩn: 30.000 VND cho đơn dưới 300.000 VND. "
                    "Hỗ trợ giao hàng nhanh trong 24h với phụ phí 50.000 VND."
                ),
            },
            {
                "id": "return_policy",
                "text": (
                    "Chính sách đổi trả: Khách hàng có thể đổi trả sản phẩm trong vòng 7 ngày "
                    "kể từ ngày nhận hàng. Sản phẩm phải còn nguyên vẹn, chưa qua sử dụng "
                    "và còn nguyên tem nhãn. Hoàn tiền trong 3-5 ngày làm việc sau khi nhận "
                    "sản phẩm trả về. Không áp dụng đổi trả với sản phẩm giảm giá đặc biệt."
                ),
            },
            {
                "id": "payment_policy",
                "text": (
                    "Phương thức thanh toán: Hỗ trợ thanh toán khi nhận hàng (COD), "
                    "chuyển khoản ngân hàng và ví điện tử. "
                    "Thanh toán online được xác nhận trong vòng 15 phút. "
                    "Đơn hàng COD cần xác nhận qua điện thoại trước khi giao."
                ),
            },
            {
                "id": "warranty_policy",
                "text": (
                    "Chính sách bảo hành: Sách được bảo hành lỗi in ấn trong 30 ngày. "
                    "Quần áo được bảo hành lỗi đường may trong 60 ngày. "
                    "Liên hệ hotline 1800-xxxx hoặc email support@bookstore.vn để được hỗ trợ."
                ),
            },
            {
                "id": "membership_policy",
                "text": (
                    "Chương trình thành viên: Đăng ký tài khoản để tích điểm mua hàng. "
                    "Cứ 10.000 VND = 1 điểm. 100 điểm = giảm 10.000 VND cho đơn tiếp theo. "
                    "Thành viên VIP (chi tiêu trên 5 triệu/năm) được giảm 10% tất cả sản phẩm."
                ),
            },
        ]

        collection.upsert(
            documents=[p["text"] for p in policies],
            ids=[p["id"] for p in policies],
        )
        return {"seeded_policies": len(policies)}

    def seed_faq(self):
        """Thêm các câu hỏi thường gặp vào KB."""
        collection = self.collections["faq"]

        faqs = [
            {
                "id": "faq_order_track",
                "text": (
                    "Câu hỏi: Làm sao để theo dõi đơn hàng của tôi? "
                    "Trả lời: Đăng nhập vào tài khoản, vào mục 'Đơn hàng của tôi' "
                    "để xem trạng thái đơn hàng và mã vận đơn."
                ),
            },
            {
                "id": "faq_cancel_order",
                "text": (
                    "Câu hỏi: Tôi có thể hủy đơn hàng không? "
                    "Trả lời: Bạn có thể hủy đơn hàng khi đơn đang ở trạng thái 'Chờ xử lý' "
                    "hoặc 'Đã xác nhận'. Vào trang chi tiết đơn hàng và nhấn 'Hủy đơn'. "
                    "Đơn đang giao hàng không thể hủy."
                ),
            },
            {
                "id": "faq_payment_fail",
                "text": (
                    "Câu hỏi: Thanh toán của tôi bị thất bại phải làm sao? "
                    "Trả lời: Kiểm tra lại thông tin thanh toán và số dư tài khoản. "
                    "Thử lại sau 5 phút. Nếu vẫn lỗi, liên hệ ngân hàng hoặc hotline của chúng tôi."
                ),
            },
            {
                "id": "faq_account",
                "text": (
                    "Câu hỏi: Làm sao để tạo tài khoản mới? "
                    "Trả lời: Nhấn vào 'Đăng ký' trên trang chủ, điền email và mật khẩu. "
                    "Xác nhận email để kích hoạt tài khoản."
                ),
            },
            {
                "id": "faq_recommend",
                "text": (
                    "Câu hỏi: Hệ thống gợi ý sản phẩm hoạt động như thế nào? "
                    "Trả lời: Hệ thống dùng AI phân tích lịch sử mua hàng và đánh giá của bạn "
                    "để gợi ý sản phẩm phù hợp nhất. Càng mua nhiều, gợi ý càng chính xác."
                ),
            },
        ]

        collection.upsert(
            documents=[f["text"] for f in faqs],
            ids=[f["id"] for f in faqs],
        )
        return {"seeded_faqs": len(faqs)}

    def search(self, query, n_results=5, collections=None):
        """
        Tìm kiếm ngữ nghĩa trong Knowledge Base.

        Args:
            query: câu hỏi/query của người dùng
            n_results: số kết quả trả về từ mỗi collection
            collections: list collection cần tìm, None = tìm tất cả

        Returns:
            list các document liên quan nhất, có kèm metadata và distance score
        """
        search_cols = collections or self.COLLECTIONS
        all_results = []

        for col_name in search_cols:
            col = self.collections.get(col_name)
            if col is None:
                continue

            count = col.count()
            if count == 0:
                continue

            # n_results không được lớn hơn số documents trong collection
            k = min(n_results, count)

            results = col.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )

            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]

            for doc, meta, dist in zip(docs, metas, dists):
                # Cosine distance: 0 = giống nhau hoàn toàn, 2 = hoàn toàn khác
                # Relevance score: 1 - distance/2 → [0, 1]
                relevance = 1.0 - (dist / 2.0)
                all_results.append({
                    "content": doc,
                    "metadata": meta,
                    "relevance": relevance,
                    "collection": col_name,
                })

        # Sắp xếp theo độ liên quan giảm dần
        all_results.sort(key=lambda x: x["relevance"], reverse=True)
        return all_results[:n_results]

    def get_stats(self):
        """Trả về thống kê về Knowledge Base."""
        return {
            col_name: self.collections[col_name].count()
            for col_name in self.COLLECTIONS
        }


# Singleton instance
knowledge_base = KnowledgeBase()
