# Generated by Django 3.1.7 on 2021-05-19 13:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_auto_20210519_1602'),
    ]

    operations = [
        migrations.AlterField(
            model_name='areaitem',
            name='area',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.area', verbose_name='Зона'),
        ),
    ]
