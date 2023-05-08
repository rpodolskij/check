# Generated by Django 3.1.7 on 2021-09-29 19:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0035_auto_20210809_0608'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceLevel',
            fields=[
                ('id', models.CharField(max_length=255, primary_key=True, serialize=False, unique=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
            ],
            options={
                'verbose_name': 'Уровень цены',
                'verbose_name_plural': 'Уровни цен',
            },
        ),
        migrations.CreateModel(
            name='ProductPrice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price_level', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.pricelevel')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.product')),
            ],
            options={
                'verbose_name': 'Цена товара',
                'verbose_name_plural': 'Цены товаров',
            },
        ),
    ]
