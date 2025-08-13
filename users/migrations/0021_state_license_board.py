from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0020_license_verification_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='StateLicenseBoard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(db_index=True, max_length=2)),
                ('board_name', models.CharField(blank=True, max_length=128)),
                ('license_type', models.CharField(blank=True, help_text='Optional license type scope if board differs by type', max_length=64)),
                ('search_url', models.CharField(help_text='Public search or lookup URL for manual + automated verification', max_length=512)),
                ('active', models.BooleanField(default=True)),
                ('notes', models.CharField(blank=True, max_length=512)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['state', 'license_type'],
                'unique_together': {('state', 'license_type', 'search_url')},
            },
        ),
    ]
