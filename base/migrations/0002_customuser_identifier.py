# Generated by Django 4.2.4 on 2023-08-26 11:44

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='identifier',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
