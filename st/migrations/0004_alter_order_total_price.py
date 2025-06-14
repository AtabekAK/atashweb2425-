# Generated by Django 5.2.3 on 2025-06-13 11:28

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('st', '0003_product_instruction_manual_product_manufacturer_url_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='total_price',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), editable=False, max_digits=12, verbose_name='Итоговая стоимость'),
        ),
    ]
