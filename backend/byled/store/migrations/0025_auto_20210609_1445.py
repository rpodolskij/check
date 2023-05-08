# Generated by Django 3.1.7 on 2021-06-09 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0024_merge_20210521_1651'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('CREATED', 'Создан'), ('COMPLETED', 'Выполнен'), ('IN_PROGRESS', 'В Работе')], default='CREATED', max_length=11, verbose_name='Статус заказа'),
        ),
    ]