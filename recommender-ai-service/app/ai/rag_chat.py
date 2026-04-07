"""
RAG - Retrieval Augmented Generation
======================================
RAG là kỹ thuật kết hợp 2 thành phần:

  1. RETRIEVAL (Truy xuất):
     - Nhận câu hỏi từ user
     - Tìm kiếm các tài liệu liên quan trong Knowledge Base (ChromaDB)
     - Trả về top-K tài liệu có độ liên quan cao nhất

  2. GENERATION (Sinh văn bản):
     - Đưa tài liệu đã truy xuất vào prompt cho LLM local (flan-t5)
     - LLM dùng context đó để trả lời chính xác, không bịa đặt
     - Nếu model chưa load được → dùng "Extractive QA" (trích xuất câu trực tiếp)

Tại sao cần RAG?
  - LLM thuần túy không biết về cửa hàng của bạn (sản phẩm, chính sách)
  - RAG "nạp" kiến thức đặc thù vào context → LLM trả lời đúng
  - Giảm "hallucination" (LLM bịa thông tin)

Luồng xử lý:
  User query → embed → ChromaDB search → top-K docs
     → build prompt → flan-t5 local → answer
"""

import os
import logging
from .knowledge_base import knowledge_base

logger = logging.getLogger(__name__)

# Model local: google/flan-t5-base (~250MB, chạy tốt trên CPU)
# Có thể đổi sang "google/flan-t5-small" nếu RAM hạn chế (~80MB)
LOCAL_MODEL_NAME = os.environ.get('LOCAL_LLM_MODEL', 'google/flan-t5-base')

SYSTEM_CONTEXT = """Bạn là trợ lý AI của cửa hàng sách và thời trang trực tuyến.
Chỉ trả lời dựa trên thông tin được cung cấp. Trả lời bằng tiếng Việt, ngắn gọn và thân thiện."""


def _load_local_model():
    """
    Load model flan-t5 local. Chỉ load 1 lần khi khởi động.
    Trả về (tokenizer, model) hoặc (None, None) nếu lỗi.
    """
    try:
        from transformers import T5ForConditionalGeneration, T5Tokenizer
        logger.info(f"Đang load model local: {LOCAL_MODEL_NAME}")
        tokenizer = T5Tokenizer.from_pretrained(LOCAL_MODEL_NAME)
        model = T5ForConditionalGeneration.from_pretrained(LOCAL_MODEL_NAME)
        model.eval()
        logger.info("Load model local thành công.")
        return tokenizer, model
    except Exception as e:
        logger.warning(f"Không thể load model local ({e}). Dùng extractive fallback.")
        return None, None


def _is_vietnamese(text):
    """Kiểm tra text có chứa ký tự tiếng Việt hay không."""
    vi_chars = 'àáâãèéêìíòóôõùúýăđơưạảặắằẳẵếềệểễịỉọổỗốồờởỡớợụủựữướừửỳỷỹ'
    return any(c in text.lower() for c in vi_chars)


def build_prompt(query, context_docs):
    """
    Xây dựng prompt cho LLM từ query và context đã truy xuất.
    flan-t5 hoạt động tốt với dạng instruction rõ ràng.
    """
    if not context_docs:
        context_text = "Không có thông tin liên quan."
    else:
        parts = []
        for i, doc in enumerate(context_docs, 1):
            parts.append(f"[{i}] {doc['content']}")
        context_text = " ".join(parts)

    # flan-t5 hiểu tốt dạng: "Answer the question based on context: ..."
    return (
        f"Answer in Vietnamese based on this context: {context_text} "
        f"Question: {query} "
        f"Answer:"
    )


def extractive_answer(query, context_docs):
    """
    Fallback khi không có model local: trích xuất câu trả lời từ tài liệu liên quan.
    """
    if not context_docs:
        return (
            "Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn. "
            "Vui lòng liên hệ hotline để được hỗ trợ trực tiếp."
        )

    best_doc = context_docs[0]
    relevance = best_doc['relevance']

    if relevance < 0.3:
        return (
            "Tôi không chắc chắn về câu trả lời cho câu hỏi này. "
            "Đây là thông tin gần nhất tôi tìm được:\n\n"
            f"{best_doc['content']}\n\n"
            "Bạn có thể liên hệ đội ngũ hỗ trợ để được giải đáp chính xác hơn."
        )

    response = f"{best_doc['content']}"

    if len(context_docs) > 1 and context_docs[1]['relevance'] > 0.5:
        response += f"\n\nThông tin thêm: {context_docs[1]['content']}"

    response += "\n\nBạn có cần hỗ trợ thêm gì không?"
    return response


class RAGChatbot:
    """
    Chatbot sử dụng RAG với model AI local (không cần API key).
    """

    def __init__(self):
        self.tokenizer, self.model = _load_local_model()
        self.has_llm = self.model is not None

    def chat(self, query, customer_id=None, conversation_history=None):
        """
        Xử lý câu hỏi của khách hàng.

        Args:
            query: câu hỏi của user
            customer_id: ID khách hàng (optional)
            conversation_history: lịch sử chat (không dùng với flan-t5)

        Returns:
            dict chứa answer, sources và metadata
        """
        # === BƯỚC 1: RETRIEVAL ===
        relevant_docs = knowledge_base.search(query, n_results=4)
        filtered_docs = [d for d in relevant_docs if d['relevance'] > 0.2]

        # === BƯỚC 2: GENERATION ===
        if self.has_llm:
            answer = self._generate_local(query, filtered_docs)
            mode = "local_rag"
        else:
            answer = extractive_answer(query, filtered_docs)
            mode = "extractive_rag"

        sources = [
            {
                "content": doc["content"][:150] + "...",
                "relevance": round(doc["relevance"], 3),
                "collection": doc["collection"],
                "metadata": doc.get("metadata", {}),
            }
            for doc in filtered_docs[:3]
        ]

        return {
            "answer": answer,
            "sources": sources,
            "mode": mode,
            "query": query,
            "docs_found": len(filtered_docs),
        }

    def _generate_local(self, query, context_docs):
        """
        Dùng flan-t5 local để sinh câu trả lời từ context.
        """
        import torch

        prompt = build_prompt(query, context_docs)

        try:
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                max_length=512,
                truncation=True,
            )

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs["input_ids"],
                    max_new_tokens=200,
                    num_beams=4,
                    early_stopping=True,
                )

            answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

            # flan-t5 là model Anh — nếu output không có tiếng Việt thì dùng extractive
            if not answer or len(answer) < 5 or not _is_vietnamese(answer):
                logger.info("flan-t5 trả ra tiếng Anh hoặc rỗng, chuyển sang extractive fallback.")
                return extractive_answer(query, context_docs)

            return answer

        except Exception as e:
            logger.error(f"Lỗi khi generate local: {e}")
            return extractive_answer(query, context_docs)


# Singleton instance
chatbot = RAGChatbot()
