# Generated by Django 3.1.7 on 2021-03-19 14:26

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Restore_keys',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('restore_key', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ],
        ),
    ]