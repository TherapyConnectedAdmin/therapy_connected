from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_additionalcredential_additional_credential_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="licensetype",
            name="short_description",
            field=models.CharField(max_length=80, blank=True, default=""),
        ),
    ]
