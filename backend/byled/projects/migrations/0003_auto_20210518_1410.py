# Generated by Django 3.1.7 on 2021-05-18 11:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0022_auto_20210517_1614'),
        ('projects', '0002_auto_20210517_2239'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='area',
            name='products',
        ),
        migrations.CreateModel(
            name='AreaItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount', models.PositiveSmallIntegerField(blank=True, default=0, verbose_name='Скидка')),
                ('count', models.PositiveSmallIntegerField(blank=True, default=0, verbose_name='Количество товара')),
                ('product', models.ManyToManyField(blank=True, default=None, to='store.Product', verbose_name='Товар')),
            ],
        ),
    ]
