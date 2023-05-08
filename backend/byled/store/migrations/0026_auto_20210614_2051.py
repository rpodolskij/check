# Generated by Django 3.1.7 on 2021-06-14 17:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0025_auto_20210609_1445'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=255, unique=True)),
                ('name', models.CharField(blank=True, default='', max_length=255, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Категория товаров',
                'verbose_name_plural': 'Категории товаров',
            },
        ),
        migrations.AlterField(
            model_name='order',
            name='manager',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='manager_of_order', to=settings.AUTH_USER_MODEL, verbose_name='Менеджер'),
        ),
    ]