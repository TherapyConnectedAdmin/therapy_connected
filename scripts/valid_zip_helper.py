import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'therapy_connected.settings')
django.setup()
import random
from users.models_profile import ZipCode

def get_valid_zip():
    """Return a random valid ZIP from the local ZipCode table.

    Raises RuntimeError if table empty.
    """
    count = ZipCode.objects.count()
    if not count:
        raise RuntimeError("ZipCode table empty. Seed with seed_zipcodes_full first.")
    offset = random.randint(0, count - 1)
    return ZipCode.objects.all()[offset].zip

if __name__ == '__main__':
    print(get_valid_zip())
