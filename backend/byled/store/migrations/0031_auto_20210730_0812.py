# Generated by Django 3.1.7 on 2021-07-30 05:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0030_auto_20210730_0806'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(blank=True, default='', max_length=255, null=True, verbose_name='Категория'),
        ),
    ]
