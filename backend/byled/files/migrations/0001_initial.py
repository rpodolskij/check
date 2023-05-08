# Generated by Django 3.1.7 on 2021-06-08 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('ext', models.CharField(max_length=255, verbose_name='Расширение')),
                ('path', models.FileField(upload_to='', verbose_name='Путь до файла')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания / загрузки')),
            ],
        ),
    ]
