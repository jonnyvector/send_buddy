from django.core.management.base import BaseCommand
from users.models import GradeConversion, Discipline


class Command(BaseCommand):
    help = 'Seed climbing grade conversions'

    def handle(self, *args, **options):
        self.stdout.write('Seeding grade conversions...')

        # Sport/Trad/Multipitch/Gym grades (score, yds, french)
        SPORT_TRAD_GRADES = [
            (0, '5.5', '4a'),
            (5, '5.6', '4b'),
            (10, '5.7', '4c'),
            (15, '5.8', '5a'),
            (20, '5.9', '5b'),
            (25, '5.10a', '5c'),
            (27, '5.10b', '6a'),
            (30, '5.10c', '6a+'),
            (32, '5.10d', '6b'),
            (35, '5.11a', '6b+'),
            (37, '5.11b', '6c'),
            (40, '5.11c', '6c+'),
            (42, '5.11d', '7a'),
            (45, '5.12a', '7a+'),
            (47, '5.12b', '7b'),
            (50, '5.12c', '7b+'),
            (52, '5.12d', '7c'),
            (55, '5.13a', '7c+'),
            (57, '5.13b', '8a'),
            (60, '5.13c', '8a+'),
            (62, '5.13d', '8b'),
            (65, '5.14a', '8b+'),
            (67, '5.14b', '8c'),
            (70, '5.14c', '8c+'),
            (72, '5.14d', '9a'),
            (75, '5.15a', '9a+'),
            (77, '5.15b', '9b'),
            (80, '5.15c', '9b+'),
        ]

        # Bouldering grades (score, v_scale, french)
        BOULDERING_GRADES = [
            (0, 'V0', '4'),
            (5, 'V1', '5'),
            (10, 'V2', '5+'),
            (15, 'V3', '6A'),
            (20, 'V4', '6B'),
            (25, 'V5', '6C'),
            (30, 'V6', '7A'),
            (35, 'V7', '7A+'),
            (40, 'V8', '7B'),
            (45, 'V9', '7B+'),
            (50, 'V10', '7C'),
            (55, 'V11', '7C+'),
            (60, 'V12', '8A'),
            (65, 'V13', '8A+'),
            (70, 'V14', '8B'),
            (75, 'V15', '8B+'),
            (80, 'V16', '8C'),
        ]

        # Seed sport/trad/multipitch/gym disciplines
        for discipline in [Discipline.SPORT, Discipline.TRAD, Discipline.MULTIPITCH, Discipline.GYM]:
            for score, yds, french in SPORT_TRAD_GRADES:
                GradeConversion.objects.update_or_create(
                    discipline=discipline,
                    score=score,
                    defaults={
                        'yds_grade': yds,
                        'french_grade': french,
                        'v_scale_grade': '',
                    }
                )
            self.stdout.write(f"  ✓ Seeded {discipline} grades ({len(SPORT_TRAD_GRADES)} grades)")

        # Seed bouldering disciplines
        for score, v_scale, french_boulder in BOULDERING_GRADES:
            GradeConversion.objects.update_or_create(
                discipline=Discipline.BOULDERING,
                score=score,
                defaults={
                    'yds_grade': '',
                    'french_grade': french_boulder,
                    'v_scale_grade': v_scale,
                }
            )
        self.stdout.write(f"  ✓ Seeded {Discipline.BOULDERING} grades ({len(BOULDERING_GRADES)} grades)")

        total_count = GradeConversion.objects.count()
        self.stdout.write(self.style.SUCCESS(f'✓ Grade conversions seeded successfully ({total_count} total)'))
