#!/usr/bin/env python
"""
Quick test script to verify OpenBeta API integration.

This script can be run independently to test the OpenBeta API
without needing the full Django app running.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from trips.services import OpenBetaAPI

def test_search_areas():
    """Test area search functionality"""
    print("\n" + "="*80)
    print("Testing OpenBeta API - Area Search")
    print("="*80)

    api = OpenBetaAPI()

    # Test 1: Search for Red River Gorge
    print("\n[Test 1] Searching for 'Red River Gorge'...")
    results = api.search_areas("Red River Gorge", limit=5)

    if results:
        print(f"✓ Found {len(results)} results")
        for i, area in enumerate(results, 1):
            print(f"\n  {i}. {area.get('area_name')}")
            print(f"     UUID: {area.get('uuid')}")
            print(f"     Path: {' > '.join(area.get('pathTokens', []))}")
            metadata = area.get('metadata') or {}
            print(f"     Coordinates: ({metadata.get('lat')}, {metadata.get('lng')})")
            print(f"     Total Climbs: {area.get('totalClimbs', 'N/A')}")
            print(f"     Density: {area.get('density', 'N/A')}")
    else:
        print("✗ No results found")

    # Test 2: Search for Yosemite
    print("\n[Test 2] Searching for 'Yosemite'...")
    results = api.search_areas("Yosemite", limit=3)

    if results:
        print(f"✓ Found {len(results)} results")
        for i, area in enumerate(results, 1):
            print(f"  {i}. {area.get('area_name')} - {area.get('totalClimbs', 0)} climbs")
    else:
        print("✗ No results found")

    # Test 3: Search with short query (should return empty)
    print("\n[Test 3] Searching with short query 'R'...")
    results = api.search_areas("R")
    print(f"✓ Correctly returned {len(results)} results (expected 0)")

    # Test 4: Search for international location
    print("\n[Test 4] Searching for 'Kalymnos'...")
    results = api.search_areas("Kalymnos", limit=3)

    if results:
        print(f"✓ Found {len(results)} results")
        for i, area in enumerate(results, 1):
            print(f"  {i}. {area.get('area_name')} ({area.get('totalClimbs', 0)} climbs)")
    else:
        print("✗ No results found")


def test_get_area_details():
    """Test getting details for a specific area"""
    print("\n" + "="*80)
    print("Testing OpenBeta API - Area Details")
    print("="*80)

    api = OpenBetaAPI()

    # First, get an area UUID from search
    print("\n[Test 5] Getting area details...")
    print("First, searching for an area to get its UUID...")

    search_results = api.search_areas("Smith Rock", limit=1)

    if search_results:
        area_uuid = search_results[0].get('uuid')
        area_name = search_results[0].get('area_name')
        print(f"✓ Found area: {area_name} (UUID: {area_uuid})")

        print(f"\nFetching detailed info for {area_name}...")
        details = api.get_area_details(area_uuid)

        if details:
            print(f"✓ Retrieved details successfully")
            print(f"\n  Name: {details.get('area_name')}")
            print(f"  UUID: {details.get('uuid')}")
            print(f"  Path: {' > '.join(details.get('pathTokens', []))}")

            metadata = details.get('metadata') or {}
            print(f"  Coordinates: ({metadata.get('lat')}, {metadata.get('lng')})")
            print(f"  Total Climbs: {details.get('totalClimbs', 'N/A')}")

            content = details.get('content') or {}
            description = content.get('description', '')
            if description:
                # Truncate long descriptions
                desc_preview = description[:150] + "..." if len(description) > 150 else description
                print(f"  Description: {desc_preview}")
            else:
                print(f"  Description: N/A")
        else:
            print("✗ Failed to retrieve details")
    else:
        print("✗ Could not find area for testing")


def test_normalize_area_data():
    """Test data normalization"""
    print("\n" + "="*80)
    print("Testing OpenBeta API - Data Normalization")
    print("="*80)

    api = OpenBetaAPI()

    print("\n[Test 6] Testing data normalization...")
    search_results = api.search_areas("El Capitan", limit=1)

    if search_results:
        raw_data = search_results[0]
        normalized = api.normalize_area_data(raw_data)

        print("✓ Normalization successful")
        print("\nNormalized fields:")
        print(f"  id: {normalized.get('id')}")
        print(f"  name: {normalized.get('name')}")
        print(f"  location: {normalized.get('location')}")
        print(f"  latitude: {normalized.get('latitude')}")
        print(f"  longitude: {normalized.get('longitude')}")
        print(f"  totalClimbs: {normalized.get('totalClimbs')}")
        print(f"  url: {normalized.get('url')}")
    else:
        print("✗ No results to normalize")


def test_caching():
    """Test that caching works"""
    print("\n" + "="*80)
    print("Testing OpenBeta API - Caching")
    print("="*80)

    import time

    api = OpenBetaAPI()

    print("\n[Test 7] Testing cache performance...")
    print("First request (should hit API)...")

    start = time.time()
    results1 = api.search_areas("Fontainebleau", limit=5)
    time1 = time.time() - start

    print(f"✓ First request completed in {time1:.3f}s")

    print("\nSecond request (should hit cache)...")
    start = time.time()
    results2 = api.search_areas("Fontainebleau", limit=5)
    time2 = time.time() - start

    print(f"✓ Second request completed in {time2:.3f}s")

    if time2 < time1 * 0.5:  # Cache should be significantly faster
        print(f"✓ Cache is working! (Second request was {time1/time2:.1f}x faster)")
    else:
        print(f"⚠ Cache may not be working as expected")

    # Verify same results
    if len(results1) == len(results2):
        print(f"✓ Both requests returned same number of results ({len(results1)})")
    else:
        print(f"✗ Results differ: {len(results1)} vs {len(results2)}")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "OpenBeta API Integration Test" + " "*29 + "║")
    print("╚" + "="*78 + "╝")

    try:
        test_search_areas()
        test_get_area_details()
        test_normalize_area_data()
        test_caching()

        print("\n" + "="*80)
        print("All tests completed!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
