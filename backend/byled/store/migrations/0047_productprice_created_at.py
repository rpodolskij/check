# Generated by Django 3.1.7 on 2023-03-26 05:34

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0046_auto_20230325_1107'),
    ]

    operations = [
        migrations.AddField(
            model_name='productprice',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
    ]