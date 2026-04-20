from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cartitem',
            old_name='book_id',
            new_name='product_id',
        ),
        migrations.AddField(
            model_name='cartitem',
            name='product_type',
            field=models.CharField(default='book', max_length=32),
        ),
        migrations.AlterUniqueTogether(
            name='cartitem',
            unique_together={('cart', 'product_type', 'product_id')},
        ),
    ]
