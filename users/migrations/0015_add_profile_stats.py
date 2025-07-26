from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0014_blogtag_blogpost'),
    ]

    operations = [
        migrations.AddField(
            model_name='therapistprofile',
            name='visit_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='therapistprofile',
            name='contact_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='therapistprofile',
            name='last_viewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
