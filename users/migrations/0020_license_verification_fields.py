from django.db import migrations, models
import django.utils.timezone
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_merge_0002_officehour_0018_licensed_name_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='therapistprofile',
            name='license_status',
            field=models.CharField(blank=True, choices=[('unverified', 'Unverified'), ('pending', 'Pending'), ('active_good_standing', 'Active / Good Standing'), ('not_found', 'Not Found'), ('expired', 'Expired'), ('disciplinary_flag', 'Disciplinary Flag'), ('error', 'Verification Error')], default='unverified', max_length=32),
        ),
        migrations.AddField(
            model_name='therapistprofile',
            name='license_last_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='therapistprofile',
            name='license_verification_source_url',
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AddField(
            model_name='therapistprofile',
            name='license_verification_raw',
            field=models.JSONField(blank=True, default=dict, help_text='Raw parsed payload from state site/API (sanitized)', null=True),
        ),
        migrations.CreateModel(
            name='LicenseVerificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(max_length=32)),
                ('message', models.CharField(blank=True, max_length=512)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('raw', models.JSONField(blank=True, default=dict, null=True)),
                ('therapist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='license_verification_logs', to='users.therapistprofile')),
            ],
        ),
    ]
