# Generated by Django 3.1.7 on 2021-07-30 05:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0031_auto_20210730_0812'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='series',
            field=models.CharField(blank=True, default='', max_length=255, null=True, verbose_name='Серия'),
        ),
    ]
