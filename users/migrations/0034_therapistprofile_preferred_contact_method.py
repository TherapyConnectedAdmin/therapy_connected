from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0033_therapistprofile_email_contact_destination'),
    ]

    operations = [
        migrations.AddField(
            model_name='therapistprofile',
            name='preferred_contact_method',
            field=models.CharField(blank=True, choices=[('email', 'Email'), ('phone', 'Phone')], default='', max_length=16),
        ),
    ]
