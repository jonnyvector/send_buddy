from typing import List, Dict
import logging
from users.models import User
from trips.models import Trip

logger = logging.getLogger(__name__)


class MatchingService:
    def __init__(self, user: User, trip: Trip, limit: int = 10):
        self.user = user
        self.trip = trip
        self.limit = limit

    def get_matches(self) -> List[Dict]:
        """Main matching function"""

        # Prefetch crags for user's trip to avoid N+1 queries
        # This is necessary for _score_location() to work efficiently
        if not self.trip.preferred_crags.all()._result_cache:
            # Only prefetch if not already cached
            from django.db.models import Prefetch
            self.trip = Trip.objects.select_related('destination').prefetch_related('preferred_crags', 'availability').get(pk=self.trip.pk)

        # Get candidate users
        candidates = self._get_candidates()

        # Score each candidate
        scored_matches = []
        for candidate in candidates:
            candidate_trip = self._get_candidate_trip(candidate)
            if not candidate_trip:
                continue

            score, reasons, details = self._calculate_match_score(candidate, candidate_trip)

            if score > 20:  # Minimum threshold
                scored_matches.append({
                    'user': candidate,
                    'trip': candidate_trip,
                    'match_score': score,
                    'reasons': reasons,
                    'overlap_dates': details['overlap_dates'],
                })

        # Sort by score descending
        scored_matches.sort(key=lambda x: x['match_score'], reverse=True)

        # Log match quality metrics
        if scored_matches:
            avg_score = sum(m['match_score'] for m in scored_matches) / len(scored_matches)
            logger.info(
                f"Generated {len(scored_matches)} matches for trip {self.trip.id}. "
                f"Avg score: {avg_score:.1f}, "
                f"Top score: {scored_matches[0]['match_score']}, "
                f"User: {self.user.email}"
            )
        else:
            logger.info(
                f"No matches found for trip {self.trip.id} (user: {self.user.email})"
            )

        return scored_matches[:self.limit]

    def _get_candidates(self):
        """Get all eligible candidate users (enforcing bilateral blocking via visible_to)"""

        # Use visible_to() to handle blocking and profile visibility consistently
        # This enforces bilateral blocking and profile_visible=True
        candidates = User.objects.visible_to(self.user).filter(
            trips__is_active=True,
            trips__start_date__lte=self.trip.end_date,
            trips__end_date__gte=self.trip.start_date,
            email_verified=True
        ).exclude(
            id=self.user.id  # Exclude self
        ).prefetch_related(
            'disciplines', 'experience_tags__tag'
        ).distinct()

        return candidates

    def _get_candidate_trip(self, candidate: User):
        """Get the candidate's trip that overlaps with my trip"""
        return candidate.trips.filter(
            is_active=True,
            start_date__lte=self.trip.end_date,
            end_date__gte=self.trip.start_date,
            destination=self.trip.destination  # Same destination (ForeignKey)
        ).select_related('destination').prefetch_related('preferred_crags', 'availability').first()

    def _calculate_match_score(self, candidate: User, candidate_trip: Trip):
        """Calculate total match score"""

        score = 0
        reasons = []
        details = {}

        # 1. Location (30 points)
        location_score = self._score_location(candidate_trip)
        score += location_score
        if location_score > 0:
            reasons.append(f"Both in {self.trip.destination.name}")

        # 2. Date overlap (20 points)
        date_score, overlap_dates = self._score_date_overlap(candidate_trip)
        score += date_score
        details['overlap_dates'] = overlap_dates
        if date_score > 0:
            reasons.append(f"{overlap_dates['days']} day overlap")

        # 3. Discipline (20 points)
        discipline_score, shared = self._score_discipline(candidate, candidate_trip)
        score += discipline_score
        if shared:
            reasons.append(f"Both climb {', '.join(shared)}")

        # 4. Grade compatibility (15 points)
        grade_score = self._score_grade_compatibility(candidate, shared)
        score += grade_score
        if grade_score > 10:
            reasons.append(f"Similar grades")

        # 5. Risk tolerance (0 to -10)
        risk_score = self._score_risk_tolerance(candidate)
        score += risk_score
        if risk_score == 10:
            reasons.append("Same risk tolerance")

        # 6. Availability (5 points)
        avail_score = self._score_availability(candidate_trip)
        score += avail_score

        # Log detailed scoring breakdown for debugging
        logger.debug(
            f"Match score breakdown for {candidate.email}: "
            f"Total={score}, Location={location_score}, Date={date_score}, "
            f"Discipline={discipline_score}, Grade={grade_score}, "
            f"Risk={risk_score}, Availability={avail_score}"
        )

        return score, reasons, details

    def _score_location(self, candidate_trip):
        """
        Score based on destination and crag overlap.

        Returns:
            - 30 points: Same destination + overlapping crags
            - 25 points: Same destination + at least one has no crag preference
            - 20 points: Same destination + different crags (no overlap)
            - 0 points: Different destinations
        """
        # Different destinations = no points
        if self.trip.destination_id != candidate_trip.destination_id:
            return 0

        # Same destination - now check crags
        # Use list() to evaluate querysets (already prefetched)
        user_crags = set(self.trip.preferred_crags.all())
        match_crags = set(candidate_trip.preferred_crags.all())

        # Case 1: At least one trip has no crag preference (flexible)
        if not user_crags or not match_crags:
            return 25  # High score for flexibility

        # Case 2: Overlapping crags (specific match)
        if user_crags & match_crags:  # Set intersection
            return 30  # Perfect match

        # Case 3: Same destination but different crags (some compatibility)
        return 20

    def _score_date_overlap(self, candidate_trip):
        overlap_start = max(self.trip.start_date, candidate_trip.start_date)
        overlap_end = min(self.trip.end_date, candidate_trip.end_date)

        if overlap_start > overlap_end:
            return 0, {}

        overlap_days = (overlap_end - overlap_start).days + 1
        score = min(20, overlap_days * 4)

        details = {
            'start': overlap_start,
            'end': overlap_end,
            'days': overlap_days
        }

        return score, details

    def _score_discipline(self, candidate, candidate_trip):
        trip_disciplines = set(self.trip.preferred_disciplines) & set(candidate_trip.preferred_disciplines)

        if not trip_disciplines:
            return 0, []

        # Check user profiles
        my_disciplines = {d.discipline for d in self.user.disciplines.all()}
        their_disciplines = {d.discipline for d in candidate.disciplines.all()}

        shared = list(trip_disciplines & my_disciplines & their_disciplines)

        if shared:
            return 20, shared
        else:
            return 5, list(trip_disciplines)

    def _score_grade_compatibility(self, candidate, shared_disciplines):
        if not shared_disciplines:
            return 0

        # For MVP, check first shared discipline
        discipline = shared_disciplines[0]

        try:
            my_profile = self.user.disciplines.get(discipline=discipline)
            their_profile = candidate.disciplines.get(discipline=discipline)
        except:
            return 0

        # Calculate grade overlap
        overlap_start = max(my_profile.comfortable_grade_min_score, their_profile.comfortable_grade_min_score)
        overlap_end = min(my_profile.comfortable_grade_max_score, their_profile.comfortable_grade_max_score)

        if overlap_start > overlap_end:
            return 0

        overlap_range = overlap_end - overlap_start
        avg_range = ((my_profile.comfortable_grade_max_score - my_profile.comfortable_grade_min_score) +
                     (their_profile.comfortable_grade_max_score - their_profile.comfortable_grade_min_score)) / 2

        overlap_ratio = overlap_range / avg_range if avg_range > 0 else 0

        return int(15 * overlap_ratio)

    def _score_risk_tolerance(self, candidate):
        RISK_SCORES = {'conservative': 0, 'balanced': 1, 'aggressive': 2}

        diff = abs(RISK_SCORES[self.user.risk_tolerance] - RISK_SCORES[candidate.risk_tolerance])

        if diff == 0:
            return 10
        elif diff == 1:
            return 3
        else:
            return -10

    def _score_availability(self, candidate_trip):
        my_avail = set(
            (a.date, a.time_block)
            for a in self.trip.availability.exclude(time_block='rest')
        )
        their_avail = set(
            (a.date, a.time_block)
            for a in candidate_trip.availability.exclude(time_block='rest')
        )

        overlap_count = len(my_avail & their_avail)
        return min(5, overlap_count)
