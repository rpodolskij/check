# Generated by Django 3.1.7 on 2021-06-18 07:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0026_auto_20210614_2051'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-create_at'], 'verbose_name': 'Заказ', 'verbose_name_plural': 'Заказы'},
        ),
    ]
