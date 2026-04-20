from django.urls import path
from .views import FoodListCreate, FoodDetail, FoodReduceStock, FoodRestoreStock

urlpatterns = [
    path('foods/', FoodListCreate.as_view()),
    path('foods/<int:pk>/', FoodDetail.as_view()),
    path('foods/<int:pk>/reduce-stock/', FoodReduceStock.as_view()),
    path('foods/<int:pk>/restore-stock/', FoodRestoreStock.as_view()),
]
