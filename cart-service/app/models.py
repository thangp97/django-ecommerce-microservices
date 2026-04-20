from django.db import models


class Cart(models.Model):
    customer_id = models.IntegerField()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product_id = models.IntegerField()
    product_type = models.CharField(max_length=32, default='book')
    quantity = models.IntegerField()

    class Meta:
        # Mỗi (cart, product_type, product_id) chỉ có 1 line item
        unique_together = (('cart', 'product_type', 'product_id'),)
