from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0002_order_grand_total_order_payment_method_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orderitem',
            old_name='book_id',
            new_name='product_id',
        ),
        migrations.AddField(
            model_name='orderitem',
            name='product_type',
            field=models.CharField(default='book', max_length=32),
        ),
    ]
