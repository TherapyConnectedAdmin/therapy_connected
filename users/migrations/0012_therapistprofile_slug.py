from django.db import migrations, models

def gen_initial_slugs(apps, schema_editor):
    TherapistProfile = apps.get_model('users', 'TherapistProfile')
    from django.utils.text import slugify
    taken = set()
    for tp in TherapistProfile.objects.all().order_by('pk'):
        base = f"{tp.first_name} {tp.last_name}".strip() or str(tp.pk)
        raw = slugify(base)[:120] or f"therapist-{tp.pk}"
        candidate = raw
        counter = 2
        while candidate in taken:
            candidate = f"{raw}-{counter}"[:155]
            counter += 1
        tp.slug = candidate
        tp.save(update_fields=['slug'])
        taken.add(candidate)

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0011_officehour'),
    ]

    operations = [
        # Step 1: add non-unique, nullable field so existing rows can share blank
        migrations.AddField(
            model_name='therapistprofile',
            name='slug',
            field=models.SlugField(blank=True, null=True, max_length=160),
        ),
        # Step 2: populate unique slugs
        migrations.RunPython(gen_initial_slugs, migrations.RunPython.noop),
        # Step 3: enforce uniqueness & not-null
        migrations.AlterField(
            model_name='therapistprofile',
            name='slug',
            field=models.SlugField(blank=True, max_length=160, unique=True),
        ),
    ]
