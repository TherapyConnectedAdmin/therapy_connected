from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0022_seed_ky_board'),
    ]

    operations = [
        migrations.AlterField(
            model_name='therapistprofile',
            name='license_number',
            field=models.CharField(max_length=32, blank=True, db_index=True),
        ),
    ]
