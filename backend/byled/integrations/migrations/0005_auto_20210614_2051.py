# Generated by Django 3.1.7 on 2021-06-14 17:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0004_auto_20210608_1132'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='synchronization',
            options={'ordering': ['-started_at'], 'verbose_name': 'Синхронизация', 'verbose_name_plural': 'Синхронизации'},
        ),
    ]
