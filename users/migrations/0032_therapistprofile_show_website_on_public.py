from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0031_therapistprofile_online_scheduling'),
    ]

    operations = [
        migrations.AddField(
            model_name='therapistprofile',
            name='show_website_on_public',
            field=models.BooleanField(default=True),
        ),
    ]
