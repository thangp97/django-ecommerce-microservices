from django.urls import path
from .views import JewelryListCreate, JewelryDetail, JewelryReduceStock, JewelryRestoreStock

urlpatterns = [
    path('jewelries/', JewelryListCreate.as_view()),
    path('jewelries/<int:pk>/', JewelryDetail.as_view()),
    path('jewelries/<int:pk>/reduce-stock/', JewelryReduceStock.as_view()),
    path('jewelries/<int:pk>/restore-stock/', JewelryRestoreStock.as_view()),
]
