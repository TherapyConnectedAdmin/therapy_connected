from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0006_lookupmaintenance'),
    ]

    operations = [
        migrations.AlterField(
            model_name='zipcode',
            name='state',
            field=models.CharField(max_length=2, db_index=True),
        ),
    ]
