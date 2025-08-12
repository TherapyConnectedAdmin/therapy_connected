from django.db import migrations


def copy_intro(apps, schema_editor):
    TherapistProfile = apps.get_model('users', 'TherapistProfile')
    for prof in TherapistProfile.objects.all():
        if (not (prof.intro_statement or '').strip()) and (prof.personal_statement_q1 or '').strip():
            prof.intro_statement = prof.personal_statement_q1
            prof.save(update_fields=['intro_statement'])


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0013_expand_accepting_new_clients_length'),
    ]

    operations = [
        migrations.RunPython(copy_intro, migrations.RunPython.noop),
    ]
