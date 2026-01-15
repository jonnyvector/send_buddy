from decimal import Decimal
from django.core.management.base import BaseCommand
from trips.models import Destination, Crag


class Command(BaseCommand):
    help = 'Seed climbing destinations and crags'

    def handle(self, *args, **options):
        self.stdout.write('Seeding destinations...')

        DESTINATIONS = {
            'red-river-gorge': {
                'name': 'Red River Gorge, KY',
                'country': 'USA',
                'lat': Decimal('37.7781'),
                'lng': Decimal('-83.6816'),
                'disciplines': ['sport', 'trad'],
                'season': 'Oct-May (best)',
                'description': 'World-class sport climbing in sandstone',
                'crags': [
                    {'name': 'Muir Valley', 'slug': 'muir-valley', 'disciplines': ['sport'], 'routes': 400},
                    {'name': "Miguel's Pizza", 'slug': 'miguels', 'disciplines': ['sport'], 'routes': 300},
                    {'name': 'PMRP', 'slug': 'pmrp', 'disciplines': ['sport', 'trad'], 'routes': 500},
                    {'name': 'The Motherlode', 'slug': 'motherlode', 'disciplines': ['sport'], 'routes': 200},
                    {'name': 'Left Flank', 'slug': 'left-flank', 'disciplines': ['sport'], 'routes': 150},
                ]
            },
            'railay': {
                'name': 'Railay, Krabi',
                'country': 'Thailand',
                'lat': Decimal('8.0097'),
                'lng': Decimal('98.8395'),
                'disciplines': ['sport'],
                'season': 'Nov-Apr (dry season)',
                'description': 'Limestone sport climbing paradise',
                'crags': [
                    {'name': 'Thaiwand Wall', 'slug': 'thaiwand', 'disciplines': ['sport'], 'routes': 200},
                    {'name': 'Fire Wall', 'slug': 'fire-wall', 'disciplines': ['sport'], 'routes': 100},
                    {'name': 'Diamond Cave', 'slug': 'diamond-cave', 'disciplines': ['sport'], 'routes': 50},
                    {'name': 'Ao Nang Tower', 'slug': 'ao-nang', 'disciplines': ['sport'], 'routes': 80},
                ]
            },
            'kalymnos': {
                'name': 'Kalymnos',
                'country': 'Greece',
                'lat': Decimal('36.9500'),
                'lng': Decimal('26.9833'),
                'disciplines': ['sport'],
                'season': 'Oct-May',
                'description': 'Greek island with endless limestone routes',
                'crags': [
                    {'name': 'Grande Grotta', 'slug': 'grande-grotta', 'disciplines': ['sport'], 'routes': 300},
                    {'name': 'Odyssey', 'slug': 'odyssey', 'disciplines': ['sport'], 'routes': 150},
                    {'name': 'Arginonta Valley', 'slug': 'arginonta', 'disciplines': ['sport'], 'routes': 200},
                ]
            },
            'yosemite': {
                'name': 'Yosemite, CA',
                'country': 'USA',
                'lat': Decimal('37.7459'),
                'lng': Decimal('-119.5937'),
                'disciplines': ['trad', 'multipitch', 'bouldering'],
                'season': 'Apr-Oct',
                'description': 'Iconic granite big walls',
                'crags': [
                    {'name': 'El Capitan', 'slug': 'el-cap', 'disciplines': ['trad', 'multipitch'], 'routes': 100},
                    {'name': 'Camp 4 Boulders', 'slug': 'camp4', 'disciplines': ['bouldering'], 'routes': 300},
                ]
            },
            'red-rocks': {
                'name': 'Red Rocks, NV',
                'country': 'USA',
                'lat': Decimal('36.1347'),
                'lng': Decimal('-115.4268'),
                'disciplines': ['sport', 'trad', 'multipitch'],
                'season': 'Oct-May',
                'description': 'Red sandstone near Las Vegas',
                'crags': [
                    {'name': 'Black Velvet Canyon', 'slug': 'black-velvet', 'disciplines': ['trad', 'multipitch'], 'routes': 50},
                    {'name': 'Calico Basin', 'slug': 'calico', 'disciplines': ['sport'], 'routes': 200},
                ]
            },
            'smith-rock': {
                'name': 'Smith Rock, OR',
                'country': 'USA',
                'lat': Decimal('44.3672'),
                'lng': Decimal('-121.1407'),
                'disciplines': ['sport', 'trad'],
                'season': 'Mar-Nov',
                'description': 'Birthplace of American sport climbing',
                'crags': []  # Can add later
            },
            'el-chorro': {
                'name': 'El Chorro',
                'country': 'Spain',
                'lat': Decimal('36.9186'),
                'lng': Decimal('-4.7686'),
                'disciplines': ['sport', 'multipitch'],
                'season': 'Oct-May',
                'description': 'Spanish limestone with long routes',
                'crags': []
            },
            'fontainebleau': {
                'name': 'Fontainebleau',
                'country': 'France',
                'lat': Decimal('48.4084'),
                'lng': Decimal('2.7002'),
                'disciplines': ['bouldering'],
                'season': 'Apr-May, Sep-Oct',
                'description': 'World-famous bouldering forest',
                'crags': []
            },
            'tonsai': {
                'name': 'Tonsai, Krabi',
                'country': 'Thailand',
                'lat': Decimal('8.0155'),
                'lng': Decimal('98.8347'),
                'disciplines': ['sport'],
                'season': 'Nov-Apr',
                'description': 'Beach-side limestone climbing',
                'crags': []
            },
            'bishop': {
                'name': 'Bishop, CA',
                'country': 'USA',
                'lat': Decimal('37.3719'),
                'lng': Decimal('-118.3971'),
                'disciplines': ['bouldering'],
                'season': 'Oct-May',
                'description': 'World-class high desert bouldering',
                'crags': [
                    {'name': 'Buttermilks', 'slug': 'buttermilks', 'disciplines': ['bouldering'], 'routes': 500},
                    {'name': 'Happy Boulders', 'slug': 'happy', 'disciplines': ['bouldering'], 'routes': 300},
                    {'name': 'Sad Boulders', 'slug': 'sad', 'disciplines': ['bouldering'], 'routes': 200},
                ]
            },
            'squamish': {
                'name': 'Squamish, BC',
                'country': 'Canada',
                'lat': Decimal('49.7016'),
                'lng': Decimal('-123.1558'),
                'disciplines': ['trad', 'sport', 'bouldering'],
                'season': 'May-Oct',
                'description': 'Granite paradise north of Vancouver',
                'crags': [
                    {'name': 'The Chief', 'slug': 'chief', 'disciplines': ['trad', 'multipitch'], 'routes': 400},
                    {'name': 'Murrin Park', 'slug': 'murrin', 'disciplines': ['sport'], 'routes': 100},
                ]
            },
            'rocklands': {
                'name': 'Rocklands',
                'country': 'South Africa',
                'lat': Decimal('-32.3667'),
                'lng': Decimal('19.0167'),
                'disciplines': ['bouldering'],
                'season': 'May-Aug',
                'description': 'Southern hemisphere bouldering mecca',
                'crags': []
            },
            'ceuse': {
                'name': 'Ceuse',
                'country': 'France',
                'lat': Decimal('44.5167'),
                'lng': Decimal('6.0167'),
                'disciplines': ['sport'],
                'season': 'Jun-Sep',
                'description': 'Iconic French sport climbing',
                'crags': []
            },
            'siurana': {
                'name': 'Siurana',
                'country': 'Spain',
                'lat': Decimal('41.2333'),
                'lng': Decimal('0.9833'),
                'disciplines': ['sport'],
                'season': 'Oct-May',
                'description': 'Classic Spanish sport climbing',
                'crags': []
            },
            'joshua-tree': {
                'name': 'Joshua Tree, CA',
                'country': 'USA',
                'lat': Decimal('33.8735'),
                'lng': Decimal('-115.9010'),
                'disciplines': ['trad', 'sport', 'bouldering'],
                'season': 'Oct-Apr',
                'description': 'Desert climbing on quartz monzonite',
                'crags': []
            },
            'frankenjura': {
                'name': 'Frankenjura',
                'country': 'Germany',
                'lat': Decimal('49.6833'),
                'lng': Decimal('11.4167'),
                'disciplines': ['sport'],
                'season': 'Apr-Oct',
                'description': 'Dense network of limestone sport crags',
                'crags': []
            },
            'hueco-tanks': {
                'name': 'Hueco Tanks, TX',
                'country': 'USA',
                'lat': Decimal('31.9194'),
                'lng': Decimal('-106.0458'),
                'disciplines': ['bouldering'],
                'season': 'Nov-Mar',
                'description': 'Historic bouldering on volcanic rock',
                'crags': []
            },
            'tonsai-beach': {
                'name': 'Cat Ba Island',
                'country': 'Vietnam',
                'lat': Decimal('20.7272'),
                'lng': Decimal('107.0453'),
                'disciplines': ['sport'],
                'season': 'Oct-Apr',
                'description': 'Limestone sport climbing in Ha Long Bay',
                'crags': []
            },
            'yangshuo': {
                'name': 'Yangshuo',
                'country': 'China',
                'lat': Decimal('24.7805'),
                'lng': Decimal('110.4972'),
                'disciplines': ['sport'],
                'season': 'Oct-Apr',
                'description': 'Karst limestone towers',
                'crags': []
            },
            'leonidio': {
                'name': 'Leonidio',
                'country': 'Greece',
                'lat': Decimal('37.1500'),
                'lng': Decimal('22.8667'),
                'disciplines': ['sport'],
                'season': 'Oct-May',
                'description': 'Red limestone sport climbing',
                'crags': []
            },
            'margalef': {
                'name': 'Margalef',
                'country': 'Spain',
                'lat': Decimal('41.2833'),
                'lng': Decimal('0.7667'),
                'disciplines': ['sport'],
                'season': 'Oct-May',
                'description': 'Conglomerate sport climbing',
                'crags': []
            },
            'kalymnos-north': {
                'name': 'Meteora',
                'country': 'Greece',
                'lat': Decimal('39.7217'),
                'lng': Decimal('21.6306'),
                'disciplines': ['sport', 'multipitch'],
                'season': 'Apr-Jun, Sep-Oct',
                'description': 'Monasteries and conglomerate pillars',
                'crags': []
            },
            'chulilla': {
                'name': 'Chulilla',
                'country': 'Spain',
                'lat': Decimal('39.6667'),
                'lng': Decimal('-0.9000'),
                'disciplines': ['sport'],
                'season': 'Oct-May',
                'description': 'Limestone canyon climbing',
                'crags': []
            },
            'rifle': {
                'name': 'Rifle, CO',
                'country': 'USA',
                'lat': Decimal('39.5347'),
                'lng': Decimal('-107.7831'),
                'disciplines': ['sport'],
                'season': 'Apr-Oct',
                'description': 'Steep limestone sport climbing',
                'crags': []
            },
            'new-river-gorge': {
                'name': 'New River Gorge, WV',
                'country': 'USA',
                'lat': Decimal('38.0682'),
                'lng': Decimal('-81.0779'),
                'disciplines': ['sport', 'trad'],
                'season': 'Mar-Nov',
                'description': 'Classic Appalachian sandstone',
                'crags': []
            },
            'devils-lake': {
                'name': 'Devils Lake, WI',
                'country': 'USA',
                'lat': Decimal('43.4194'),
                'lng': Decimal('-89.7243'),
                'disciplines': ['trad', 'bouldering'],
                'season': 'May-Oct',
                'description': 'Midwest quartzite climbing',
                'crags': []
            },
            'gunks': {
                'name': 'The Gunks, NY',
                'country': 'USA',
                'lat': Decimal('41.7394'),
                'lng': Decimal('-74.1794'),
                'disciplines': ['trad'],
                'season': 'Apr-Oct',
                'description': 'Classic East Coast trad climbing',
                'crags': []
            },
            'bugaboos': {
                'name': 'Bugaboos, BC',
                'country': 'Canada',
                'lat': Decimal('50.7500'),
                'lng': Decimal('-116.7833'),
                'disciplines': ['trad', 'multipitch', 'alpine'],
                'season': 'Jul-Sep',
                'description': 'Alpine granite spires',
                'crags': []
            },
            'chamonix': {
                'name': 'Chamonix',
                'country': 'France',
                'lat': Decimal('45.9237'),
                'lng': Decimal('6.8694'),
                'disciplines': ['alpine', 'multipitch', 'trad'],
                'season': 'Jun-Sep',
                'description': 'Alpine climbing capital of the world',
                'crags': []
            },
            'dolomites': {
                'name': 'Dolomites',
                'country': 'Italy',
                'lat': Decimal('46.4102'),
                'lng': Decimal('11.8440'),
                'disciplines': ['sport', 'multipitch', 'alpine'],
                'season': 'Jun-Sep',
                'description': 'Italian limestone towers',
                'crags': []
            },
            'maple-canyon': {
                'name': 'Maple Canyon, UT',
                'country': 'USA',
                'lat': Decimal('39.4042'),
                'lng': Decimal('-111.6417'),
                'disciplines': ['sport'],
                'season': 'Apr-Jun, Sep-Oct',
                'description': 'Cobblestone conglomerate',
                'crags': []
            },
            'ten-sleep': {
                'name': 'Ten Sleep, WY',
                'country': 'USA',
                'lat': Decimal('44.0361'),
                'lng': Decimal('-107.4519'),
                'disciplines': ['sport'],
                'season': 'May-Oct',
                'description': 'Limestone sport climbing haven',
                'crags': []
            },
            'escalante': {
                'name': 'Escalante, UT',
                'country': 'USA',
                'lat': Decimal('37.7711'),
                'lng': Decimal('-111.6003'),
                'disciplines': ['trad', 'sport'],
                'season': 'Mar-May, Sep-Nov',
                'description': 'Desert sandstone towers and walls',
                'crags': []
            },
            'indian-creek': {
                'name': 'Indian Creek, UT',
                'country': 'USA',
                'lat': Decimal('38.0333'),
                'lng': Decimal('-109.6167'),
                'disciplines': ['trad'],
                'season': 'Mar-May, Sep-Nov',
                'description': 'Perfect splitter cracks',
                'crags': []
            },
            'moab': {
                'name': 'Moab, UT',
                'country': 'USA',
                'lat': Decimal('38.5733'),
                'lng': Decimal('-109.5498'),
                'disciplines': ['trad', 'sport', 'multipitch'],
                'season': 'Mar-May, Sep-Nov',
                'description': 'Desert tower and wall climbing',
                'crags': []
            },
            'peak-district': {
                'name': 'Peak District',
                'country': 'UK',
                'lat': Decimal('53.3500'),
                'lng': Decimal('-1.8333'),
                'disciplines': ['trad', 'bouldering'],
                'season': 'Apr-Oct',
                'description': 'Classic British gritstone',
                'crags': []
            },
            'lake-district': {
                'name': 'Lake District',
                'country': 'UK',
                'lat': Decimal('54.4609'),
                'lng': Decimal('-3.0886'),
                'disciplines': ['trad'],
                'season': 'Apr-Oct',
                'description': 'Mountain crags and volcanic rock',
                'crags': []
            },
            'grampians': {
                'name': 'Grampians',
                'country': 'Australia',
                'lat': Decimal('-37.2167'),
                'lng': Decimal('142.5000'),
                'disciplines': ['trad', 'sport'],
                'season': 'Mar-Nov',
                'description': 'Australian sandstone climbing',
                'crags': []
            },
            'arapiles': {
                'name': 'Mount Arapiles',
                'country': 'Australia',
                'lat': Decimal('-36.7833'),
                'lng': Decimal('141.8333'),
                'disciplines': ['trad', 'sport'],
                'season': 'Mar-Nov',
                'description': 'Iconic Australian climbing destination',
                'crags': []
            },
            'freyr': {
                'name': 'Freyr',
                'country': 'Belgium',
                'lat': Decimal('50.2333'),
                'lng': Decimal('4.9167'),
                'disciplines': ['sport'],
                'season': 'Apr-Oct',
                'description': 'Compact limestone sport climbing',
                'crags': []
            },
            'arco': {
                'name': 'Arco',
                'country': 'Italy',
                'lat': Decimal('45.9167'),
                'lng': Decimal('10.8833'),
                'disciplines': ['sport'],
                'season': 'Mar-Nov',
                'description': 'Competition climbing venue',
                'crags': []
            },
            'rodellar': {
                'name': 'Rodellar',
                'country': 'Spain',
                'lat': Decimal('42.2833'),
                'lng': Decimal('-0.0667'),
                'disciplines': ['sport'],
                'season': 'Apr-Jun, Sep-Oct',
                'description': 'Overhanging limestone caves',
                'crags': []
            },
            'finale-ligure': {
                'name': 'Finale Ligure',
                'country': 'Italy',
                'lat': Decimal('44.1667'),
                'lng': Decimal('8.3500'),
                'disciplines': ['sport'],
                'season': 'Oct-May',
                'description': 'Mediterranean limestone sport climbing',
                'crags': []
            },
            'trnovo': {
                'name': 'Trnovo',
                'country': 'Slovenia',
                'lat': Decimal('45.9167'),
                'lng': Decimal('13.7167'),
                'disciplines': ['sport'],
                'season': 'Apr-Oct',
                'description': 'Slovenian limestone sport routes',
                'crags': []
            },
            'paklenica': {
                'name': 'Paklenica',
                'country': 'Croatia',
                'lat': Decimal('44.3667'),
                'lng': Decimal('15.4500'),
                'disciplines': ['sport', 'multipitch'],
                'season': 'Apr-Jun, Sep-Oct',
                'description': 'Adriatic limestone climbing',
                'crags': []
            },
            'montserrat': {
                'name': 'Montserrat',
                'country': 'Spain',
                'lat': Decimal('41.5933'),
                'lng': Decimal('1.8367'),
                'disciplines': ['sport', 'multipitch'],
                'season': 'Oct-May',
                'description': 'Conglomerate towers near Barcelona',
                'crags': []
            },
            'albarracin': {
                'name': 'Albarracin',
                'country': 'Spain',
                'lat': Decimal('40.4089'),
                'lng': Decimal('-1.4397'),
                'disciplines': ['bouldering'],
                'season': 'Oct-May',
                'description': 'Spanish sandstone bouldering',
                'crags': []
            },
            'rumney': {
                'name': 'Rumney, NH',
                'country': 'USA',
                'lat': Decimal('43.8047'),
                'lng': Decimal('-71.8167'),
                'disciplines': ['sport'],
                'season': 'May-Oct',
                'description': 'New England sport climbing',
                'crags': []
            },
        }

        for slug, data in DESTINATIONS.items():
            destination, created = Destination.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': data['name'],
                    'country': data['country'],
                    'lat': data['lat'],
                    'lng': data['lng'],
                    'primary_disciplines': data['disciplines'],
                    'season': data.get('season', ''),
                    'description': data.get('description', ''),
                }
            )

            status = 'Created' if created else 'Updated'
            self.stdout.write(f"  {status}: {destination.name}")

            # Create crags
            for crag_data in data.get('crags', []):
                crag, created = Crag.objects.update_or_create(
                    destination=destination,
                    slug=crag_data['slug'],
                    defaults={
                        'name': crag_data['name'],
                        'disciplines': crag_data['disciplines'],
                        'route_count': crag_data.get('routes'),
                    }
                )
                status = 'Created' if created else 'Updated'
                self.stdout.write(f"    {status} crag: {crag.name}")

        total_destinations = Destination.objects.count()
        total_crags = Crag.objects.count()
        self.stdout.write(self.style.SUCCESS(f'✓ Locations seeded successfully ({total_destinations} destinations, {total_crags} crags)'))
