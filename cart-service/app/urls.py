from django.urls import path
from .views import CartCreate, AddCartItem, CartView, DeleteCartItem, ClearCart

urlpatterns = [
    path('carts/', CartCreate.as_view()),
    path('cart-items/', AddCartItem.as_view()),
    path('cart-items/<int:cart_id>/<str:product_type>/<int:product_id>/', DeleteCartItem.as_view()),
    path('carts/<int:customer_id>/', CartView.as_view()),
    path('carts/<int:customer_id>/clear/', ClearCart.as_view()),
]
