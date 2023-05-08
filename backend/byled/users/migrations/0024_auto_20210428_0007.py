# Generated by Django 3.1.7 on 2021-04-27 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_delete_client'),
        ('users', '0023_auto_20210427_2347'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basketitem',
            name='count',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.RemoveField(
            model_name='basketitem',
            name='product',
        ),
        migrations.AddField(
            model_name='basketitem',
            name='product',
            field=models.ManyToManyField(default=None, to='store.Product'),
        ),
    ]
