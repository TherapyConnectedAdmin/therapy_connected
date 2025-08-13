from django.db import migrations

def seed_ky_board(apps, schema_editor):
    Board = apps.get_model('users','StateLicenseBoard')
    # Generic Kentucky OOP portal seed (specific board/license_type rows can be added later)
    if not Board.objects.filter(state='KY', search_url__icontains='oop.ky.gov').exists():
        Board.objects.create(state='KY', board_name='Kentucky Office of Occupations & Professions', license_type='', search_url='https://oop.ky.gov', notes='Initial seed; implement board-specific endpoints later')

def unseed_ky_board(apps, schema_editor):
    Board = apps.get_model('users','StateLicenseBoard')
    Board.objects.filter(state='KY', search_url__icontains='oop.ky.gov').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0021_state_license_board'),
    ]

    operations = [
        migrations.RunPython(seed_ky_board, unseed_ky_board)
    ]
