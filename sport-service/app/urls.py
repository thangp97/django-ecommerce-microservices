from django.urls import path
from .views import SportListCreate, SportDetail, SportReduceStock, SportRestoreStock

urlpatterns = [
    path('sports/', SportListCreate.as_view()),
    path('sports/<int:pk>/', SportDetail.as_view()),
    path('sports/<int:pk>/reduce-stock/', SportReduceStock.as_view()),
    path('sports/<int:pk>/restore-stock/', SportRestoreStock.as_view()),
]
