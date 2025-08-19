from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0032_therapistprofile_show_website_on_public'),
    ]

    operations = [
        migrations.AddField(
            model_name='therapistprofile',
            name='email_contact_destination',
            field=models.CharField(choices=[('therapist', 'Therapist'), ('office', 'Office'), ('both', 'Both')], default='therapist', max_length=16),
        ),
    ]
