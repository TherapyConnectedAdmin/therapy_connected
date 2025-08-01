import random
from uszipcode import SearchEngine

# Get a valid US zip code from the uszipcode database
search = SearchEngine()
def get_valid_zip():
    # Try up to 10 times to get a valid zip
    for _ in range(10):
        z = search.by_index(random.randint(0, 42000))
        if z and z.zipcode and z.lat and z.lng:
            return z.zipcode
    # Fallback to a known valid zip
    return "32550"
