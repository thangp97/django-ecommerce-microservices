from django.urls import path
from .views import ApplianceListCreate, ApplianceDetail, ApplianceReduceStock, ApplianceRestoreStock

urlpatterns = [
    path('appliances/', ApplianceListCreate.as_view()),
    path('appliances/<int:pk>/', ApplianceDetail.as_view()),
    path('appliances/<int:pk>/reduce-stock/', ApplianceReduceStock.as_view()),
    path('appliances/<int:pk>/restore-stock/', ApplianceRestoreStock.as_view()),
]
