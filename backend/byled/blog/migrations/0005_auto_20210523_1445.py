# Generated by Django 3.1.7 on 2021-05-23 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0004_auto_20210512_1641'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='text',
            field=models.TextField(verbose_name='Текст комментария'),
        ),
    ]