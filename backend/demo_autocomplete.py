#!/usr/bin/env python
"""
Demo script showing how the autocomplete endpoint works with OpenBeta data.

This demonstrates the end-to-end flow of the autocomplete feature.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from trips.models import Destination
from trips.services import OpenBetaAPI
from django.utils.text import slugify
from decimal import Decimal
from django.utils import timezone


def demo_autocomplete_flow():
    """Demonstrate the autocomplete workflow with OpenBeta"""

    print("\n" + "="*80)
    print("Demo: Autocomplete with OpenBeta Integration")
    print("="*80)

    # Step 1: Initialize API
    print("\n[Step 1] Initializing OpenBeta API...")
    api = OpenBetaAPI()
    print("✓ API client ready")

    # Step 2: Search for a climbing area
    search_query = "Red River Gorge"
    print(f"\n[Step 2] Searching OpenBeta for '{search_query}'...")
    results = api.search_areas(search_query, limit=3)

    if not results:
        print("✗ No results found")
        return

    print(f"✓ Found {len(results)} areas")

    # Step 3: Display raw OpenBeta data
    print("\n[Step 3] Raw OpenBeta data (first result):")
    first_result = results[0]
    print(f"  area_name: {first_result.get('area_name')}")
    print(f"  uuid: {first_result.get('uuid')}")
    print(f"  totalClimbs: {first_result.get('totalClimbs')}")
    print(f"  pathTokens: {first_result.get('pathTokens')}")

    # Step 4: Normalize the data
    print("\n[Step 4] Normalizing data for our model...")
    normalized = api.normalize_area_data(first_result)
    print(f"  id (maps to mp_id): {normalized.get('id')}")
    print(f"  name: {normalized.get('name')}")
    print(f"  location: {normalized.get('location')}")
    print(f"  coordinates: ({normalized.get('latitude')}, {normalized.get('longitude')})")
    print(f"  url: {normalized.get('url')}")

    # Step 5: Check if this area exists in our database
    print("\n[Step 5] Checking if area exists in database...")
    slug = slugify(normalized.get('name'))
    existing = Destination.objects.filter(slug=slug).first()

    if existing:
        print(f"✓ Area exists: {existing.name} (slug: {existing.slug})")
        print(f"  Current mp_id: {existing.mp_id}")
        print(f"  Last synced: {existing.last_synced or 'Never'}")
    else:
        print(f"✗ Area not in database (slug would be: {slug})")
        print("\n  To add this area, you could run:")
        print(f"  python manage.py sync_openbeta '{search_query}'")

    # Step 6: Demonstrate autocomplete query
    print("\n[Step 6] Simulating autocomplete query...")
    print("  Query: 'red river'")

    autocomplete_results = Destination.objects.filter(
        name__icontains='red river'
    ).order_by('-mp_star_rating', 'name')[:5]

    if autocomplete_results:
        print(f"✓ Found {autocomplete_results.count()} destinations in database:")
        for dest in autocomplete_results:
            rating = dest.mp_star_rating or 'N/A'
            print(f"  - {dest.name} (rating: {rating})")
    else:
        print("✗ No destinations in database (seed data may be needed)")
        print("\n  To add destinations, run:")
        print("  python manage.py seed_locations")

    # Step 7: Show how we'd create a new destination from OpenBeta
    print("\n[Step 7] Example: Creating destination from OpenBeta data...")
    print("  (This is a dry-run, not actually creating)")

    example_data = {
        'slug': slug,
        'name': normalized.get('name'),
        'country': first_result.get('pathTokens', [])[0] if first_result.get('pathTokens') else 'Unknown',
        'lat': Decimal(str(normalized.get('latitude', 0))),
        'lng': Decimal(str(normalized.get('longitude', 0))),
        'description': normalized.get('description', ''),
        'mp_id': normalized.get('id'),  # OpenBeta UUID
        'mp_url': normalized.get('url'),
        'location_hierarchy': normalized.get('location', []),
        'mp_star_rating': None,  # OpenBeta doesn't have ratings
        'mp_star_votes': None,
        'primary_disciplines': ['sport', 'trad'],  # Would infer from data
        'last_synced': timezone.now(),
    }

    print("\n  Destination data that would be created:")
    for key, value in example_data.items():
        if key in ['description'] and len(str(value)) > 50:
            print(f"    {key}: {str(value)[:50]}...")
        else:
            print(f"    {key}: {value}")

    print("\n[Step 8] Testing cache performance...")
    import time

    print("  First search (hits API)...")
    start = time.time()
    api.search_areas("Bishop", limit=5)
    time1 = time.time() - start

    print("  Second search (hits cache)...")
    start = time.time()
    api.search_areas("Bishop", limit=5)
    time2 = time.time() - start

    print(f"✓ First: {time1:.3f}s, Second: {time2:.3f}s (Cache is {time1/time2:.0f}x faster)")

    print("\n" + "="*80)
    print("Demo Complete!")
    print("="*80)
    print("\nKey Takeaways:")
    print("1. OpenBeta API returns rich data about climbing areas")
    print("2. Data is normalized to fit our Destination model")
    print("3. UUIDs are stored in the existing mp_id field")
    print("4. Star ratings are null for OpenBeta data (can sort by totalClimbs)")
    print("5. Caching makes subsequent queries extremely fast")
    print("6. No breaking changes to existing autocomplete functionality")
    print()


if __name__ == '__main__':
    try:
        demo_autocomplete_flow()
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
