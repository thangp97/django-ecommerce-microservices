from django.urls import path
from .views import CosmeticListCreate, CosmeticDetail, CosmeticReduceStock, CosmeticRestoreStock

urlpatterns = [
    path('cosmetics/', CosmeticListCreate.as_view()),
    path('cosmetics/<int:pk>/', CosmeticDetail.as_view()),
    path('cosmetics/<int:pk>/reduce-stock/', CosmeticReduceStock.as_view()),
    path('cosmetics/<int:pk>/restore-stock/', CosmeticRestoreStock.as_view()),
]
