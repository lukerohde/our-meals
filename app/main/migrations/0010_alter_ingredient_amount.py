# Generated by Django 5.1.4 on 2024-12-31 05:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_fix_none_strings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ingredient',
            name='amount',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]