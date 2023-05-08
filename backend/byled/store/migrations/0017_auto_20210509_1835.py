# Generated by Django 3.1.7 on 2021-05-09 15:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0016_auto_20210509_1604'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('COMPLETED', 'Выполнен'), ('IN_PROGRESS', 'В Работе')], default='IN_PROGRESS', max_length=11, verbose_name='Статус заказа'),
        ),
        migrations.AlterField(
            model_name='order',
            name='comment',
            field=models.TextField(blank=True),
        ),
    ]