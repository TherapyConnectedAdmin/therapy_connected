from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0010_galleryimage_is_primary'),
    ]

    operations = [
        migrations.CreateModel(
            name='OfficeHour',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.PositiveSmallIntegerField(help_text='0=Mon .. 6=Sun')),
                ('is_closed', models.BooleanField(default=False)),
                ('by_appointment_only', models.BooleanField(default=False, help_text="Ignore times; display 'By appointment' if true")),
                ('start_time_1', models.CharField(blank=True, help_text='HH:MM', max_length=5)),
                ('end_time_1', models.CharField(blank=True, help_text='HH:MM', max_length=5)),
                ('start_time_2', models.CharField(blank=True, help_text='Optional second interval start HH:MM', max_length=5)),
                ('end_time_2', models.CharField(blank=True, help_text='Optional second interval end HH:MM', max_length=5)),
                ('notes', models.CharField(blank=True, max_length=64)),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='office_hours', to='users.location')),
            ],
            options={
                'ordering': ['location', 'weekday'],
                'unique_together': {('location', 'weekday')},
            },
        ),
    ]
