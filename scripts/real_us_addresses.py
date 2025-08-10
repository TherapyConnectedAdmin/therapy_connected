"""Small curated set of real, publicly known US street addresses for generating
map-valid location data in non-production environments.

Usage: Imported by generate_fake_therapists when FAKE_USE_REAL_ADDRESSES=1 (default).
Addresses are factual data (not copyrightable) and drawn from well-known sources
(government buildings, libraries, universities). Avoid including private
residences. Expand this list as needed; keep it under ~200 to limit repo bloat.

Schema for each entry:
{
  'practice_name': str,   # Optional default practice / landmark name
  'street_address': str,
  'city': str,
  'state': str,           # 2-letter abbreviation
  'zip': str
}
"""
REAL_US_ADDRESSES = [
    {"practice_name": "Fulton St Health Center", "street_address": "330 Fulton St", "city": "Brooklyn", "state": "NY", "zip": "11201"},
    {"practice_name": "Downtown Wellness", "street_address": "50 Fremont St", "city": "San Francisco", "state": "CA", "zip": "94105"},
    {"practice_name": "Lakeview Counseling", "street_address": "875 N Michigan Ave", "city": "Chicago", "state": "IL", "zip": "60611"},
    {"practice_name": "Capitol Therapy", "street_address": "400 Capitol Mall", "city": "Sacramento", "state": "CA", "zip": "95814"},
    {"practice_name": "Peachtree Center", "street_address": "225 Peachtree St NE", "city": "Atlanta", "state": "GA", "zip": "30303"},
    {"practice_name": "Pioneer Place", "street_address": "700 SW 5th Ave", "city": "Portland", "state": "OR", "zip": "97204"},
    {"practice_name": "Market Square", "street_address": "151 W 4th St", "city": "Cincinnati", "state": "OH", "zip": "45202"},
    {"practice_name": "Union Station Offices", "street_address": "1701 Wynkoop St", "city": "Denver", "state": "CO", "zip": "80202"},
    {"practice_name": "Space Needle Plaza", "street_address": "400 Broad St", "city": "Seattle", "state": "WA", "zip": "98109"},
    {"practice_name": "Liberty Place", "street_address": "1601 Market St", "city": "Philadelphia", "state": "PA", "zip": "19103"},
    {"practice_name": "River North Center", "street_address": "350 W Mart Center Dr", "city": "Chicago", "state": "IL", "zip": "60654"},
    {"practice_name": "Downtown Commons", "street_address": "500 W 2nd St", "city": "Austin", "state": "TX", "zip": "78701"},
    {"practice_name": "Medical Arts Building", "street_address": "370 O'Farrell St", "city": "San Francisco", "state": "CA", "zip": "94102"},
    {"practice_name": "Civic Center", "street_address": "200 N Spring St", "city": "Los Angeles", "state": "CA", "zip": "90012"},
    {"practice_name": "Harborfront Center", "street_address": "600 E Grand Ave", "city": "Chicago", "state": "IL", "zip": "60611"},
    {"practice_name": "Desert Ridge", "street_address": "21001 N Tatum Blvd", "city": "Phoenix", "state": "AZ", "zip": "85050"},
    {"practice_name": "Rockefeller Plaza", "street_address": "45 Rockefeller Plaza", "city": "New York", "state": "NY", "zip": "10111"},
    {"practice_name": "Times Square Center", "street_address": "1500 Broadway", "city": "New York", "state": "NY", "zip": "10036"},
    {"practice_name": "Downtown Tower", "street_address": "621 Capitol Mall", "city": "Sacramento", "state": "CA", "zip": "95814"},
    {"practice_name": "Canal Place", "street_address": "333 Canal St", "city": "New Orleans", "state": "LA", "zip": "70130"},
    {"practice_name": "Mint Plaza", "street_address": "54 Mint St", "city": "San Francisco", "state": "CA", "zip": "94103"},
    {"practice_name": "Fremont Center", "street_address": "300 S Fremont Ave", "city": "Los Angeles", "state": "CA", "zip": "90071"},
    {"practice_name": "Seaport District", "street_address": "1 Seaport Ln", "city": "Boston", "state": "MA", "zip": "02210"},
    {"practice_name": "Brookline Offices", "street_address": "1309 Beacon St", "city": "Brookline", "state": "MA", "zip": "02446"},
    {"practice_name": "Innovation Square", "street_address": "555 W 5th St", "city": "Los Angeles", "state": "CA", "zip": "90013"},
    {"practice_name": "Battery Park Center", "street_address": "17 Battery Pl", "city": "New York", "state": "NY", "zip": "10004"},
    {"practice_name": "Magnolia Center", "street_address": "600 Houston St", "city": "Fort Worth", "state": "TX", "zip": "76102"},
    {"practice_name": "Union Square West", "street_address": "860 Broadway", "city": "New York", "state": "NY", "zip": "10003"},
    {"practice_name": "South Beach Center", "street_address": "100 Collins Ave", "city": "Miami Beach", "state": "FL", "zip": "33139"},
    {"practice_name": "Brickell Plaza", "street_address": "701 Brickell Ave", "city": "Miami", "state": "FL", "zip": "33131"},
    {"practice_name": "Downtown Scottsdale", "street_address": "7144 E Stetson Dr", "city": "Scottsdale", "state": "AZ", "zip": "85251"},
    {"practice_name": "Hillcrest Center", "street_address": "3900 5th Ave", "city": "San Diego", "state": "CA", "zip": "92103"},
    {"practice_name": "Queen Anne Tower", "street_address": "200 1st Ave W", "city": "Seattle", "state": "WA", "zip": "98119"},
    {"practice_name": "Ballard Works", "street_address": "2856 NW Market St", "city": "Seattle", "state": "WA", "zip": "98107"},
    {"practice_name": "Uptown Center", "street_address": "1120 N Charles St", "city": "Baltimore", "state": "MD", "zip": "21201"},
    {"practice_name": "Georgetown Center", "street_address": "3307 M St NW", "city": "Washington", "state": "DC", "zip": "20007"},
    {"practice_name": "Dupont Circle", "street_address": "1350 Connecticut Ave NW", "city": "Washington", "state": "DC", "zip": "20036"},
    {"practice_name": "Downtown Durham", "street_address": "318 Blackwell St", "city": "Durham", "state": "NC", "zip": "27701"},
    {"practice_name": "South End", "street_address": "1616 Camden Rd", "city": "Charlotte", "state": "NC", "zip": "28203"},
    {"practice_name": "Buckhead Center", "street_address": "3344 Peachtree Rd NE", "city": "Atlanta", "state": "GA", "zip": "30326"},
    {"practice_name": "Midtown Nashville", "street_address": "150 3rd Ave S", "city": "Nashville", "state": "TN", "zip": "37201"},
    {"practice_name": "Music Row", "street_address": "1913 Broadway", "city": "Nashville", "state": "TN", "zip": "37203"},
    {"practice_name": "Downtown Salt Lake", "street_address": "175 S Main St", "city": "Salt Lake City", "state": "UT", "zip": "84111"},
    {"practice_name": "Temple Square", "street_address": "50 N Temple", "city": "Salt Lake City", "state": "UT", "zip": "84150"},
    {"practice_name": "Downtown Boise", "street_address": "999 W Main St", "city": "Boise", "state": "ID", "zip": "83702"},
    {"practice_name": "Reno Center", "street_address": "50 W Liberty St", "city": "Reno", "state": "NV", "zip": "89501"},
    {"practice_name": "Downtown Honolulu", "street_address": "1001 Bishop St", "city": "Honolulu", "state": "HI", "zip": "96813"},
    {"practice_name": "Old Town Alexandria", "street_address": "1725 Duke St", "city": "Alexandria", "state": "VA", "zip": "22314"},
    {"practice_name": "Downtown Richmond", "street_address": "901 E Cary St", "city": "Richmond", "state": "VA", "zip": "23219"},
    {"practice_name": "Palm Beach Center", "street_address": "401 Clematis St", "city": "West Palm Beach", "state": "FL", "zip": "33401"},
    {"practice_name": "Downtown Orlando", "street_address": "390 N Orange Ave", "city": "Orlando", "state": "FL", "zip": "32801"},
]

# Provide a simple iterator helper if needed elsewhere
class RealAddressPool:
    def __init__(self, addresses):
        self._addresses = list(addresses)
        self._index = 0
    def next(self):
        if not self._addresses:
            raise ValueError("No addresses in pool")
        addr = self._addresses[self._index % len(self._addresses)]
        self._index += 1
        return addr

ADDRESS_POOL = RealAddressPool(REAL_US_ADDRESSES)
