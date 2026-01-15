from django.core.management.base import BaseCommand
from users.models import ExperienceTag


class Command(BaseCommand):
    help = 'Seed experience and equipment tags'

    def handle(self, *args, **options):
        self.stdout.write('Seeding experience tags...')

        SEED_TAGS = [
            # Skills
            ('lead_belay_certified', 'Lead Belay Certified', 'skill', 'Certified to lead belay'),
            ('multipitch_experience', 'Multipitch Experience', 'skill', 'Experience with multipitch climbing'),
            ('trad_anchor_building', 'Can Build Trad Anchors', 'skill', 'Proficient in building trad anchors'),
            ('outdoor_beginner_friendly', 'Beginner Friendly', 'skill', 'Happy to climb with beginners'),
            ('sport_leading', 'Can Sport Lead', 'skill', 'Can lead sport routes'),
            ('trad_leading', 'Can Trad Lead', 'skill', 'Can lead trad routes'),

            # Equipment
            ('has_rope', 'Has Rope', 'equipment', 'Owns climbing rope'),
            ('has_quickdraws', 'Has Quickdraws', 'equipment', 'Owns quickdraws'),
            ('has_trad_rack', 'Has Trad Rack', 'equipment', 'Owns trad climbing rack'),
            ('has_crash_pad', 'Has Crash Pad', 'equipment', 'Owns bouldering crash pad'),

            # Logistics
            ('has_car', 'Has Car', 'logistics', 'Can provide transportation'),
            ('has_scooter', 'Has Scooter/Bike', 'logistics', 'Has scooter or bicycle'),
            ('local_knowledge', 'Local Knowledge', 'logistics', 'Knows the area well'),

            # Preferences - Climbing Schedule
            ('early_riser', 'Early Riser', 'preference', 'Likes to start climbing early (sunrise missions!)'),
            ('slow_starter', 'Slow Starter', 'preference', 'Prefers a relaxed morning, starts climbing mid-morning'),
            ('afternoon_climber', 'Afternoon Climber', 'preference', 'Prefers afternoon/evening climbing sessions'),
            ('flexible_schedule', 'Flexible Schedule', 'preference', 'Happy to climb anytime - morning, afternoon, or evening'),

            # Preferences - Style
            ('social_climber', 'Social Climber', 'preference', 'Enjoys social/group climbing'),
            ('project_focused', 'Project Focused', 'preference', 'Focused on projecting routes'),
            ('multi_pitch_preferred', 'Loves Multipitch', 'preference', 'Prefers multipitch climbing'),
            ('photography_enthusiast', 'Photography Enthusiast', 'preference', 'Enjoys taking climbing photos'),
        ]

        for slug, display_name, category, description in SEED_TAGS:
            tag, created = ExperienceTag.objects.update_or_create(
                slug=slug,
                defaults={
                    'display_name': display_name,
                    'category': category,
                    'description': description,
                }
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f"  {status}: {display_name}")

        total_count = ExperienceTag.objects.count()
        self.stdout.write(self.style.SUCCESS(f'✓ Experience tags seeded successfully ({total_count} total)'))
