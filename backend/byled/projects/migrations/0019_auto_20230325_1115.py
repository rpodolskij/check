# Generated by Django 3.1.7 on 2023-03-25 08:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0018_auto_20230325_1107'),
    ]

    operations = [
        migrations.RenameField(
            model_name='areaitem',
            old_name='price_ryb',
            new_name='price_rub',
        ),
    ]
