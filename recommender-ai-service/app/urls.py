from django.urls import path
from .views import (
    # Rule-based (giữ lại)
    RecommendForCustomer,
    PopularBooks,
    # Deep Learning
    TrainNCFModel,
    NCFRecommend,
    # Knowledge Base
    SyncKnowledgeBase,
    KnowledgeBaseStats,
    KnowledgeSearch,
    # RAG Chat
    ChatView,
    # Dashboard
    AIDashboard,
)

urlpatterns = [
    # ── Cũ (rule-based) ──────────────────────────────────────
    path('recommendations/<int:customer_id>/', RecommendForCustomer.as_view()),
    path('popular/', PopularBooks.as_view()),

    # ── AI Dashboard ─────────────────────────────────────────
    path('ai/', AIDashboard.as_view()),

    # ── Deep Learning: NCF Model ─────────────────────────────
    path('ai/train/', TrainNCFModel.as_view()),
    path('ai/recommend/<int:customer_id>/', NCFRecommend.as_view()),

    # ── Knowledge Base ────────────────────────────────────────
    path('ai/knowledge/sync/', SyncKnowledgeBase.as_view()),
    path('ai/knowledge/stats/', KnowledgeBaseStats.as_view()),
    path('ai/knowledge/search/', KnowledgeSearch.as_view()),

    # ── RAG Chatbot ───────────────────────────────────────────
    path('ai/chat/', ChatView.as_view()),
]
