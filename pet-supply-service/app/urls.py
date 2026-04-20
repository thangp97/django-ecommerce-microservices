from django.urls import path
from .views import PetSupplyListCreate, PetSupplyDetail, PetSupplyReduceStock, PetSupplyRestoreStock

urlpatterns = [
    path('pet-supplies/', PetSupplyListCreate.as_view()),
    path('pet-supplies/<int:pk>/', PetSupplyDetail.as_view()),
    path('pet-supplies/<int:pk>/reduce-stock/', PetSupplyReduceStock.as_view()),
    path('pet-supplies/<int:pk>/restore-stock/', PetSupplyRestoreStock.as_view()),
]
