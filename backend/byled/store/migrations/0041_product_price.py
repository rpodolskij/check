# Generated by Django 3.1.7 on 2021-10-27 12:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0040_auto_20211026_2246'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='price',
            field=models.FloatField(blank=True, default=0, verbose_name='Цена'),
        ),
    ]
