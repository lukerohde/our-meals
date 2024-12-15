# Generated by Django 5.1.4 on 2024-12-14 23:28

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_create_default_mealplans'),
    ]

    operations = [
        migrations.AddField(
            model_name='meal',
            name='meal_plan',
            field=models.ManyToManyField(related_name='meals', to='main.mealplan'),
        ),
        migrations.AlterField(
            model_name='mealplan',
            name='shareable_link',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
