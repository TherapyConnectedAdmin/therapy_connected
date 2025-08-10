from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_lookup_categories'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZipCode',
            fields=[
                ('zip', models.CharField(primary_key=True, serialize=False, max_length=5)),
                ('city', models.CharField(max_length=64)),
                ('state', models.CharField(max_length=2, db_index=True)),
                ('latitude', models.DecimalField(max_digits=8, decimal_places=5)),
                ('longitude', models.DecimalField(max_digits=8, decimal_places=5)),
            ],
        ),
    ]
