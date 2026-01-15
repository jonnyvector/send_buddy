"""
Management command to sync climbing area data from OpenBeta API.

This command demonstrates how to use the OpenBeta API to populate
or update Destination records in the database.

Usage:
    python manage.py sync_openbeta "Red River Gorge"
    python manage.py sync_openbeta --search "Yosemite"
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from decimal import Decimal
from trips.models import Destination
from trips.services import OpenBetaAPI


class Command(BaseCommand):
    help = 'Sync climbing area data from OpenBeta API'

    def add_arguments(self, parser):
        parser.add_argument(
            'query',
            nargs='?',
            type=str,
            help='Search query for climbing area (e.g., "Red River Gorge")'
        )
        parser.add_argument(
            '--search',
            type=str,
            help='Alternative way to specify search query'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of results to fetch (default: 10)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without saving to database'
        )

    def handle(self, *args, **options):
        query = options.get('query') or options.get('search')

        if not query:
            raise CommandError(
                'Please provide a search query.\n'
                'Usage: python manage.py sync_openbeta "Red River Gorge"\n'
                '   or: python manage.py sync_openbeta --search "Yosemite"'
            )

        limit = options['limit']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS(f'\nSearching OpenBeta for: "{query}"'))

        # Initialize API client
        api = OpenBetaAPI()

        # Search for areas
        results = api.search_areas(query, limit=limit)

        if not results:
            self.stdout.write(self.style.WARNING(f'No results found for "{query}"'))
            return

        self.stdout.write(f'Found {len(results)} results:\n')

        # Display results
        for i, area in enumerate(results, 1):
            area_name = area.get('area_name', 'Unknown')
            total_climbs = area.get('totalClimbs', 0)
            path = ' > '.join(area.get('pathTokens', []))

            self.stdout.write(
                f'{i}. {area_name} ({total_climbs} climbs)\n'
                f'   Path: {path}'
            )

        # Ask user which area to sync (if interactive)
        if not dry_run:
            self.stdout.write('\nWhich area would you like to sync? (Enter number, or 0 to cancel): ', ending='')
            try:
                choice = int(input())
                if choice == 0:
                    self.stdout.write('Cancelled.')
                    return

                if choice < 1 or choice > len(results):
                    raise ValueError('Invalid choice')

                selected_area = results[choice - 1]
                self._sync_area(api, selected_area)

            except (ValueError, KeyboardInterrupt):
                self.stdout.write(self.style.ERROR('\nInvalid choice or cancelled.'))
                return
        else:
            # Dry run mode - show what would be synced
            self.stdout.write(self.style.WARNING('\n[DRY RUN MODE] - No data will be saved\n'))
            for area in results:
                self._show_area_preview(area)

    def _sync_area(self, api, area_data):
        """Sync a single area to the database"""
        area_name = area_data.get('area_name', 'Unknown')
        area_uuid = area_data.get('uuid')

        self.stdout.write(f'\nFetching detailed info for "{area_name}"...')

        # Get full details
        details = api.get_area_details(area_uuid)
        if not details:
            self.stdout.write(self.style.ERROR(f'Could not fetch details for {area_name}'))
            return

        # Normalize data
        normalized = api.normalize_area_data(details)

        # Extract fields
        metadata = details.get('metadata') or {}
        content = details.get('content') or {}
        path_tokens = details.get('pathTokens', [])

        # Determine country (first item in path, or default to 'Unknown')
        country = path_tokens[0] if path_tokens else 'Unknown'

        # Create slug from area name
        slug = slugify(area_name)

        # Check if destination already exists
        existing = Destination.objects.filter(slug=slug).first()

        if existing:
            self.stdout.write(f'Updating existing destination: {slug}')
        else:
            self.stdout.write(f'Creating new destination: {slug}')

        # Prepare data
        destination_data = {
            'name': area_name,
            'country': country,
            'lat': Decimal(str(metadata.get('lat', 0))),
            'lng': Decimal(str(metadata.get('lng', 0))),
            'description': content.get('description', ''),
            'mp_id': area_uuid,  # Store OpenBeta UUID in mp_id field
            'mp_url': normalized.get('url', ''),
            'location_hierarchy': path_tokens,
            'mp_star_rating': None,  # OpenBeta doesn't have star ratings
            'mp_star_votes': None,
        }

        # Try to infer disciplines from area name or path
        disciplines = self._infer_disciplines(area_name, path_tokens)
        if disciplines:
            destination_data['primary_disciplines'] = disciplines

        # Create or update
        destination, created = Destination.objects.update_or_create(
            slug=slug,
            defaults=destination_data
        )

        # Mark as synced
        from django.utils import timezone
        destination.last_synced = timezone.now()
        destination.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'\n✓ {action} destination: {destination.name}'))
        self.stdout.write(f'  Slug: {destination.slug}')
        self.stdout.write(f'  Country: {destination.country}')
        self.stdout.write(f'  Coordinates: ({destination.lat}, {destination.lng})')
        self.stdout.write(f'  Total Climbs: {details.get("totalClimbs", "N/A")}')
        self.stdout.write(f'  OpenBeta UUID: {area_uuid}')

    def _show_area_preview(self, area_data):
        """Show what would be synced (for dry run)"""
        area_name = area_data.get('area_name', 'Unknown')
        metadata = area_data.get('metadata') or {}
        path_tokens = area_data.get('pathTokens', [])

        self.stdout.write(f'\nArea: {area_name}')
        self.stdout.write(f'  Slug: {slugify(area_name)}')
        self.stdout.write(f'  Country: {path_tokens[0] if path_tokens else "Unknown"}')
        self.stdout.write(f'  Coordinates: ({metadata.get("lat")}, {metadata.get("lng")})')
        self.stdout.write(f'  Total Climbs: {area_data.get("totalClimbs", 0)}')
        self.stdout.write(f'  Path: {" > ".join(path_tokens)}')

    def _infer_disciplines(self, area_name, path_tokens):
        """Try to infer climbing disciplines from area name or path"""
        disciplines = []

        # Keywords to look for
        keywords = {
            'sport': ['sport', 'clip', 'bolted'],
            'trad': ['trad', 'crack', 'gear'],
            'bouldering': ['boulder', 'bouldering'],
            'multipitch': ['multipitch', 'multi-pitch', 'wall', 'big wall'],
            'alpine': ['alpine', 'mountain'],
        }

        # Search in name and path
        search_text = ' '.join([area_name] + path_tokens).lower()

        for discipline, patterns in keywords.items():
            for pattern in patterns:
                if pattern in search_text:
                    disciplines.append(discipline)
                    break

        return disciplines if disciplines else ['sport']  # Default to sport
