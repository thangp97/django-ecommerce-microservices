"""
RAG - Retrieval Augmented Generation
======================================
RAG là kỹ thuật kết hợp 2 thành phần:

  1. RETRIEVAL (Truy xuất):
     - Nhận câu hỏi từ user
     - Tìm kiếm các tài liệu liên quan trong Knowledge Base (ChromaDB)
     - Trả về top-K tài liệu có độ liên quan cao nhất

  2. GENERATION (Sinh văn bản):
     - Đưa tài liệu đã truy xuất vào prompt cho LLM (Claude)
     - LLM dùng context đó để trả lời chính xác, không bịa đặt
     - Nếu không có API key → dùng "Extractive QA" (trích xuất câu trực tiếp)

Tại sao cần RAG?
  - LLM thuần túy không biết về cửa hàng của bạn (sản phẩm, chính sách)
  - RAG "nạp" kiến thức đặc thù vào context → LLM trả lời đúng
  - Giảm "hallucination" (LLM bịa thông tin)

Luồng xử lý:
  User query → embed → ChromaDB search → top-K docs
     → build prompt → Claude API → answer
"""

import os
import anthropic
from .knowledge_base import knowledge_base

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Bạn là trợ lý AI của cửa hàng sách và thời trang trực tuyến.
Nhiệm vụ của bạn là tư vấn khách hàng dựa trên thông tin được cung cấp.

Nguyên tắc:
1. Chỉ trả lời dựa trên CONTEXT được cung cấp. Không bịa đặt thông tin.
2. Nếu không tìm thấy thông tin trong context, hãy nói thật: "Tôi không có thông tin về vấn đề này."
3. Trả lời bằng tiếng Việt, thân thiện và ngắn gọn.
4. Nếu câu hỏi liên quan đến sản phẩm cụ thể, đề cập giá và tình trạng kho nếu có.
5. Luôn kết thúc bằng câu hỏi xem khách có cần hỗ trợ thêm không."""


def build_prompt(query, context_docs):
    """
    Xây dựng prompt cho LLM từ query và context đã truy xuất.

    Cấu trúc prompt RAG chuẩn:
      [CONTEXT] - thông tin từ KB
      [QUESTION] - câu hỏi của user
      → LLM trả lời dựa trên context
    """
    if not context_docs:
        context_text = "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
    else:
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            relevance_pct = int(doc['relevance'] * 100)
            context_parts.append(
                f"[Tài liệu {i} - Độ liên quan: {relevance_pct}%]\n{doc['content']}"
            )
        context_text = "\n\n".join(context_parts)

    return f"""=== CONTEXT (Thông tin từ cơ sở kiến thức) ===
{context_text}

=== CÂU HỎI CỦA KHÁCH HÀNG ===
{query}

=== YÊU CẦU ===
Hãy trả lời câu hỏi dựa trên context trên. Nếu context không đủ thông tin, hãy nói rõ."""


def extractive_answer(query, context_docs):
    """
    Fallback khi không có API key: trích xuất câu trả lời từ tài liệu liên quan.

    Đây là phương pháp đơn giản hơn: không sinh văn bản mới,
    chỉ trả về đoạn văn bản liên quan nhất từ KB.
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

    # Nếu độ liên quan cao, trả về nội dung trực tiếp
    response = f"{best_doc['content']}"

    # Thêm thông tin bổ sung từ các tài liệu khác nếu có
    if len(context_docs) > 1 and context_docs[1]['relevance'] > 0.5:
        response += f"\n\nThông tin thêm: {context_docs[1]['content']}"

    response += "\n\nBạn có cần hỗ trợ thêm gì không?"
    return response


class RAGChatbot:
    """
    Chatbot sử dụng RAG để trả lời câu hỏi về cửa hàng.
    """

    def __init__(self):
        self.has_llm = bool(ANTHROPIC_API_KEY)
        if self.has_llm:
            self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def chat(self, query, customer_id=None, conversation_history=None):
        """
        Xử lý câu hỏi của khách hàng.

        Args:
            query: câu hỏi của user
            customer_id: ID khách hàng (optional, dùng để cá nhân hóa)
            conversation_history: lịch sử chat [{"role": "user/assistant", "content": "..."}]

        Returns:
            dict chứa answer, sources và metadata
        """
        conversation_history = conversation_history or []

        # === BƯỚC 1: RETRIEVAL ===
        # Tìm kiếm tài liệu liên quan trong Knowledge Base
        # Nếu query liên quan đến sản phẩm → ưu tiên tìm trong "products"
        # Nếu liên quan chính sách → tìm trong "policies" và "faq"
        relevant_docs = knowledge_base.search(query, n_results=4)

        # Lọc chỉ lấy docs có độ liên quan > 20%
        filtered_docs = [d for d in relevant_docs if d['relevance'] > 0.2]

        # === BƯỚC 2: GENERATION ===
        if self.has_llm:
            answer = self._generate_with_claude(query, filtered_docs, conversation_history)
            mode = "llm_rag"
        else:
            # Fallback: extractive QA
            answer = extractive_answer(query, filtered_docs)
            mode = "extractive_rag"

        # Chuẩn bị sources để trả về (để user biết thông tin lấy từ đâu)
        sources = [
            {
                "content": doc["content"][:150] + "...",  # preview
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

    def _generate_with_claude(self, query, context_docs, conversation_history):
        """
        Gọi Claude API để sinh câu trả lời dựa trên context.

        Claude là LLM (Large Language Model) của Anthropic.
        Ta truyền vào:
          - system: định nghĩa vai trò của AI
          - context: tài liệu liên quan từ KB
          - messages: lịch sử hội thoại + câu hỏi hiện tại
        """
        prompt = build_prompt(query, context_docs)

        # Xây dựng messages với lịch sử hội thoại (multi-turn conversation)
        messages = []
        for msg in conversation_history[-6:]:  # Chỉ giữ 6 tin nhắn gần nhất
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.APIError as e:
            # Fallback nếu API lỗi
            return extractive_answer(query, context_docs)


# Singleton instance
chatbot = RAGChatbot()
