# Generated by Django 3.1.7 on 2021-06-05 07:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0002_auto_20210510_0304'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='synchronization',
            options={'verbose_name': 'Синхронизация', 'verbose_name_plural': 'Синхронизации'},
        ),
    ]