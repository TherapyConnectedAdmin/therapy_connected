from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_zipcode_state_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='therapistprofile',
            name='profile_photo_meta',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
