# Generated by Django 3.1.7 on 2022-09-27 09:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0043_auto_20220927_1243'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productcategory',
            name='parent',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='store.productcategory'),
        ),
    ]
