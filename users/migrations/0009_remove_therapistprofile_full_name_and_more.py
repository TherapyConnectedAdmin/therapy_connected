# Generated by Django 4.2.23 on 2025-07-23 23:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_citycounty_clientpopulation_insurance_language_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='therapistprofile',
            name='full_name',
        ),
        migrations.AddField(
            model_name='therapistprofile',
            name='first_name',
            field=models.CharField(default='', max_length=64),
        ),
        migrations.AddField(
            model_name='therapistprofile',
            name='last_name',
            field=models.CharField(default='', max_length=64),
        ),
    ]
