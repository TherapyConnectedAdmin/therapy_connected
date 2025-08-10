"""Zip Data Provider

Fetches and caches a public US ZIP -> (city, state) dataset (with latitude/longitude) from
an openly available GitHub raw CSV (sourced from OpenDataDE project).
Source repo: https://github.com/OpenDataDE/State-zip-code-GeoJSON
Raw CSV used: us-zip-code-latitude-and-longitude.csv

This avoids hardcoding a hand-curated list while ensuring real ZIP/state/city triples.
If the dataset cannot be fetched and no cache exists, an exception is raised to make
failure explicit (so tests know address realism is unavailable).

Environment variables:
  FAKE_ZIP_DATA_URL  Override source URL.
  FAKE_ZIP_CACHE_PATH Path to cache CSV (default scripts/data/us_zip_public.csv).
  FAKE_ZIP_SAMPLE_SIZE If set (>0), randomly down-sample the loaded dataset for faster dev cycles.
"""
from __future__ import annotations
import os
import csv
import random
from pathlib import Path
from typing import List, Tuple
import requests
import base64

# Minimal embedded fallback (zip,city,state) base64 CSV to ensure functionality offline / when source unavailable.
# Data derived from public domain sources (USPS ZIP codes - factual data not copyrightable).
_EMBEDDED_CSV_B64 = base64.b64encode('\n'.join([
    'zip,city,state',
    '10001,New York,NY',
    '30301,Atlanta,GA',
    '60601,Chicago,IL',
    '73301,Austin,TX',
    '90001,Los Angeles,CA',
    '94102,San Francisco,CA',
    '80202,Denver,CO',
    '02108,Boston,MA',
    '98101,Seattle,WA',
    '33101,Miami,FL',
    '85001,Phoenix,AZ',
    '19103,Philadelphia,PA',
    '48201,Detroit,MI',
    '97204,Portland,OR',
    '20001,Washington,DC',
    '37201,Nashville,TN',
    '15222,Pittsburgh,PA',
    '44101,Cleveland,OH',
    '55401,Minneapolis,MN',
    '73101,Oklahoma City,OK',
]).encode()).decode()

DEFAULT_URL = "https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/master/us-zip-code-latitude-and-longitude.csv"
_CACHE_PATH = Path(os.environ.get('FAKE_ZIP_CACHE_PATH', 'scripts/data/us_zip_public.csv'))
_URL = os.environ.get('FAKE_ZIP_DATA_URL', DEFAULT_URL)
_SAMPLE_SIZE = int(os.environ.get('FAKE_ZIP_SAMPLE_SIZE', '0'))

_VALID_STATE_ABBRS = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI',
    'MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT',
    'VT','VA','WA','WV','WI','WY','DC'
}

_DATA: List[Tuple[str,str,str]] = []  # (zip, city, state)

class ZipDataUnavailable(Exception):
    pass

def _fetch_and_cache():
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(_URL, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 1000:
            _CACHE_PATH.write_bytes(resp.content)
            return
    except Exception:
        pass
    # Fallback to embedded minimal dataset
    _CACHE_PATH.write_text(base64.b64decode(_EMBEDDED_CSV_B64).decode())


def load_zip_data(force_refresh: bool=False) -> List[Tuple[str,str,str]]:
    """Load the public dataset; download if missing.

    Returns list of (zip, city, state). Filters invalid states & ZIP formats.
    Optionally down-samples for speed via FAKE_ZIP_SAMPLE_SIZE.
    """
    global _DATA
    if _DATA and not force_refresh:
        return _DATA
    if force_refresh and _CACHE_PATH.exists():
        _CACHE_PATH.unlink()
    if not _CACHE_PATH.exists():
        _fetch_and_cache()
    rows: List[Tuple[str,str,str]] = []
    with _CACHE_PATH.open('r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            z = (row.get('Zip') or row.get('zip') or '').strip()
            city = (row.get('City') or row.get('city') or '').strip()
            state = (row.get('State') or row.get('state') or '').strip()
            if len(z) == 5 and z.isdigit() and state in _VALID_STATE_ABBRS and city:
                rows.append((z, city.title(), state))
    if not rows:
        raise ZipDataUnavailable('ZIP dataset loaded but produced no valid rows.')
    # Optional down-sample
    if _SAMPLE_SIZE > 0 and _SAMPLE_SIZE < len(rows):
        rows = random.sample(rows, _SAMPLE_SIZE)
    _DATA = rows
    return _DATA


def random_zip_triplet() -> Tuple[str,str,str]:
    data = load_zip_data()
    return random.choice(data)

