# Generated by Django 3.0.8 on 2021-03-24 15:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site_settings', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='activity_submission_form',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Lien pour soumettre une activité'),
        ),
    ]
