# Generated by Django 3.1.7 on 2021-07-30 04:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0012_auto_20210709_0910'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='project',
            options={'verbose_name': 'Проект', 'verbose_name_plural': 'Проекты'},
        ),
    ]