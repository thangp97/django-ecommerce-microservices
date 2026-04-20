from django.urls import path
from .views import StationeryListCreate, StationeryDetail, StationeryReduceStock, StationeryRestoreStock

urlpatterns = [
    path('stationeries/', StationeryListCreate.as_view()),
    path('stationeries/<int:pk>/', StationeryDetail.as_view()),
    path('stationeries/<int:pk>/reduce-stock/', StationeryReduceStock.as_view()),
    path('stationeries/<int:pk>/restore-stock/', StationeryRestoreStock.as_view()),
]
