# Generated by Django 3.1.7 on 2021-04-18 08:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_auto_20210415_1313'),
    ]

    operations = [
        migrations.AddField(
            model_name='actionkey',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата создания'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='actionkey',
            name='action',
            field=models.CharField(choices=[('restore', 'Restore'), ('confirm', 'Confirm')], max_length=64, verbose_name='Тип ключа'),
        ),
        migrations.AlterField(
            model_name='actionkey',
            name='key',
            field=models.CharField(max_length=64, unique=True, verbose_name='Ключ'),
        ),
        migrations.AlterField(
            model_name='actionkey',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='action_keys', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
    ]
