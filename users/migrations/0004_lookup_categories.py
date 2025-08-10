from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_licensetype_short_description"),
    ]

    operations = [
        migrations.AddField(
            model_name='specialtylookup',
            name='category',
            field=models.CharField(blank=True, db_index=True, max_length=48),
        ),
        migrations.AddField(
            model_name='specialtylookup',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='therapytype',
            name='name',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AddField(
            model_name='therapytype',
            name='category',
            field=models.CharField(blank=True, db_index=True, max_length=48),
        ),
        migrations.AddField(
            model_name='therapytype',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='category',
            field=models.CharField(blank=True, db_index=True, max_length=48),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='insuranceprovider',
            name='category',
            field=models.CharField(blank=True, db_index=True, max_length=48),
        ),
        migrations.AddField(
            model_name='insuranceprovider',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='licensetype',
            name='category',
            field=models.CharField(blank=True, db_index=True, max_length=48),
        ),
        migrations.AddField(
            model_name='licensetype',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='licensetype',
            name='description',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
    ]
