from django.urls import path
from .views import FurnitureListCreate, FurnitureDetail, FurnitureReduceStock, FurnitureRestoreStock

urlpatterns = [
    path('furnitures/', FurnitureListCreate.as_view()),
    path('furnitures/<int:pk>/', FurnitureDetail.as_view()),
    path('furnitures/<int:pk>/reduce-stock/', FurnitureReduceStock.as_view()),
    path('furnitures/<int:pk>/restore-stock/', FurnitureRestoreStock.as_view()),
]
