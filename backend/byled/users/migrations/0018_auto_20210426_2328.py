# Generated by Django 3.1.7 on 2021-04-26 20:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_auto_20210426_2052'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='basket',
            name='l',
        ),
        migrations.RemoveField(
            model_name='user',
            name='basket',
        ),
        migrations.AddField(
            model_name='basket',
            name='user',
            field=models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
