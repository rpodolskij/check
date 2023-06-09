# Generated by Django 3.1.7 on 2021-04-15 07:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import users.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20210319_1924'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActionKey',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('restore', 'Restore'), ('confirm', 'Confirm')], max_length=64)),
                ('key', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='action_keys', to=settings.AUTH_USER_MODEL)),
            ],
            managers=[
                ('objects', users.models.KeyManager()),
            ],
        ),
        migrations.DeleteModel(
            name='Restore_keys',
        ),
    ]
