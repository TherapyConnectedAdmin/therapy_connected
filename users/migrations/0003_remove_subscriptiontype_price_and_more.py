# Generated by Django 4.2.23 on 2025-07-22 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_subscriptiontype_remove_subscription_plan_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscriptiontype',
            name='price',
        ),
        migrations.RemoveField(
            model_name='subscriptiontype',
            name='stripe_plan_id',
        ),
        migrations.AddField(
            model_name='subscriptiontype',
            name='price_annual',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='subscriptiontype',
            name='price_monthly',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='subscriptiontype',
            name='stripe_plan_id_annual',
            field=models.CharField(blank=True, max_length=128, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='subscriptiontype',
            name='stripe_plan_id_monthly',
            field=models.CharField(blank=True, max_length=128, null=True, unique=True),
        ),
    ]
