# Generated by Django 3.1.7 on 2021-04-27 09:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_basket_products'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='basket',
            name='user',
        ),
        migrations.AddField(
            model_name='user',
            name='basket',
            field=models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.basket'),
        ),
    ]
