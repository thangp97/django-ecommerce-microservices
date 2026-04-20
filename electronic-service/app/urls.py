from django.urls import path
from .views import ElectronicListCreate, ElectronicDetail, ElectronicReduceStock, ElectronicRestoreStock

urlpatterns = [
    path('electronics/', ElectronicListCreate.as_view()),
    path('electronics/<int:pk>/', ElectronicDetail.as_view()),
    path('electronics/<int:pk>/reduce-stock/', ElectronicReduceStock.as_view()),
    path('electronics/<int:pk>/restore-stock/', ElectronicRestoreStock.as_view()),
]
