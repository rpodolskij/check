# Generated by Django 3.1.7 on 2021-05-04 19:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0026_auto_20210428_0117'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='account_type',
            field=models.CharField(choices=[('CLIENT', 'Клиент'), ('MANAGER', 'Мэнеджер'), ('ADMIN', 'Администратор')], default='CLIENT', max_length=7, verbose_name='Тип аккаунта'),
        ),
    ]
