# Generated by Django 5.2.1 on 2025-06-16 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Backend_paint_app', '0017_reclamation_reclamationphoto'),
    ]

    operations = [
        migrations.AddField(
            model_name='reclamation',
            name='status',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
