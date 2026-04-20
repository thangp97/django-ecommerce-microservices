from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health),
    path('bootstrap/', views.bootstrap),
    path('recommend/', views.recommend),
    path('similar/', views.similar),
    path('chat/', views.chat),
    path('stats/', views.graph_stats),
]
