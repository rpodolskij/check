# Generated by Django 3.1.7 on 2021-04-15 10:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20210415_1213'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, default=None, null=True, upload_to='', verbose_name='Аватар'),
        ),
    ]
