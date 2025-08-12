from django.db import migrations, models

TRI_STATE_MAP = {
    'yes': 'Accepting New Clients',
    'accepting new clients': 'Accepting New Clients',
    'accepting': 'Accepting New Clients',
    'no': 'Not Accepting New Clients',
    'not accepting': 'Not Accepting New Clients',
    'i have a waitlist': 'I Have a Waitlist',
    'waitlist': 'I Have a Waitlist',
    'i have a wait list': 'I Have a Waitlist',
}

def normalize_accepting_values(apps, schema_editor):
    Profile = apps.get_model('users', 'TherapistProfile')
    for p in Profile.objects.all():
        raw = (p.accepting_new_clients or '').strip()
        lowered = raw.lower()
        new_val = TRI_STATE_MAP.get(lowered)
        if new_val and new_val != raw:
            p.accepting_new_clients = new_val
            p.save(update_fields=['accepting_new_clients'])

def reverse_noop(apps, schema_editor):
    # No reverse necessary; shortening the data would risk truncation.
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0012_therapistprofile_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='therapistprofile',
            name='accepting_new_clients',
            field=models.CharField(default='Yes', max_length=32),
        ),
        migrations.RunPython(normalize_accepting_values, reverse_noop),
    ]
