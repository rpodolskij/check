# Generated by Django 3.1.7 on 2021-07-30 04:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0028_product_is_archive'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='series',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Серия'),
        ),
    ]
