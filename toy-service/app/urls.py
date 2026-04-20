from django.urls import path
from .views import ToyListCreate, ToyDetail, ToyReduceStock, ToyRestoreStock

urlpatterns = [
    path('toys/', ToyListCreate.as_view()),
    path('toys/<int:pk>/', ToyDetail.as_view()),
    path('toys/<int:pk>/reduce-stock/', ToyReduceStock.as_view()),
    path('toys/<int:pk>/restore-stock/', ToyRestoreStock.as_view()),
]
