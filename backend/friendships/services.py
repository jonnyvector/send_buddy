from django.db import transaction
from django.db.models import Q, Count, Exists, OuterRef
from django.utils import timezone
from datetime import timedelta
from typing import Optional, List
from .models import Friendship
from users.models import User, Block
from notifications.services import NotificationService


class FriendshipService:
    # Constants
    MAX_FRIENDS = 500
    REQUEST_EXPIRY_DAYS = 90

    @staticmethod
    def send_friend_request(requester: User, addressee: User) -> Friendship:
        """
        Create friend request and send notification.
        - Validate users aren't already friends
        - Validate no blocking relationship
        - Create Friendship with status='pending'
        - Trigger notification
        """
        # Validate users are different
        if requester.id == addressee.id:
            raise ValueError("Cannot send friend request to yourself")

        # Check for blocking relationship (bilateral check)
        if Block.objects.filter(
            Q(blocker=requester, blocked=addressee) |
            Q(blocker=addressee, blocked=requester)
        ).exists():
            raise ValueError("Cannot send friend request due to blocking relationship")

        # Check if already friends or pending request exists
        existing = Friendship.objects.filter(
            Q(requester=requester, addressee=addressee) |
            Q(requester=addressee, addressee=requester)
        ).first()

        if existing:
            if existing.status == 'accepted':
                raise ValueError("Users are already friends")
            elif existing.status == 'pending':
                if existing.requester == requester:
                    raise ValueError("Friend request already sent")
                else:
                    # Auto-accept if both users sent requests to each other
                    existing.status = 'accepted'
                    existing.accepted_at = timezone.now()
                    existing.save()

                    # Send notification to the original requester
                    NotificationService.create_friend_accepted_notification(existing)

                    return existing

        # Check friend count limit
        friend_count = Friendship.objects.filter(
            Q(requester=requester, status='accepted') |
            Q(addressee=requester, status='accepted')
        ).count()

        if friend_count >= FriendshipService.MAX_FRIENDS:
            raise ValueError(f"Cannot have more than {FriendshipService.MAX_FRIENDS} friends")

        # Create new friendship request
        with transaction.atomic():
            friendship = Friendship.objects.create(
                requester=requester,
                addressee=addressee,
                status='pending',
                connection_source='manual_add'
            )

            # Send notification to addressee
            NotificationService.create_friend_request_notification(requester, addressee)

        return friendship

    @staticmethod
    def accept_friend_request(friendship_id: str, accepting_user: User) -> Friendship:
        """
        Accept request and notify both users.
        - Validate the accepting user is the addressee
        - Update status to 'accepted'
        - Set accepted_at timestamp
        - Trigger notification
        """
        try:
            friendship = Friendship.objects.get(id=friendship_id)
        except Friendship.DoesNotExist:
            raise ValueError("Friend request not found")

        # Validate accepting user is the addressee
        if friendship.addressee != accepting_user:
            raise ValueError("You cannot accept this friend request")

        # Validate request is still pending
        if friendship.status != 'pending':
            raise ValueError("Friend request is no longer pending")

        # Check if request has expired
        expiry_date = friendship.created_at + timedelta(days=FriendshipService.REQUEST_EXPIRY_DAYS)
        if timezone.now() > expiry_date:
            friendship.delete()
            raise ValueError("Friend request has expired")

        # Check friend count limit for accepting user
        friend_count = Friendship.objects.filter(
            Q(requester=accepting_user, status='accepted') |
            Q(addressee=accepting_user, status='accepted')
        ).count()

        if friend_count >= FriendshipService.MAX_FRIENDS:
            raise ValueError(f"Cannot have more than {FriendshipService.MAX_FRIENDS} friends")

        with transaction.atomic():
            # Update friendship status
            friendship.status = 'accepted'
            friendship.accepted_at = timezone.now()
            friendship.save()

            # Send notification to requester
            NotificationService.create_friend_accepted_notification(friendship)

        return friendship

    @staticmethod
    def decline_friend_request(friendship_id: str, declining_user: User) -> None:
        """
        Decline/delete the friend request.
        """
        try:
            friendship = Friendship.objects.get(id=friendship_id)
        except Friendship.DoesNotExist:
            raise ValueError("Friend request not found")

        # Validate declining user is the addressee
        if friendship.addressee != declining_user:
            raise ValueError("You cannot decline this friend request")

        # Validate request is still pending
        if friendship.status != 'pending':
            raise ValueError("Friend request is no longer pending")

        # Delete the friendship (no notification for declines)
        friendship.delete()

    @staticmethod
    def remove_friend(friendship_id: str, requesting_user: User) -> None:
        """
        Remove an existing friendship.
        - Validate user is part of the friendship
        - Delete the friendship
        """
        try:
            friendship = Friendship.objects.get(id=friendship_id)
        except Friendship.DoesNotExist:
            raise ValueError("Friendship not found")

        # Validate requesting user is part of the friendship
        if friendship.requester != requesting_user and friendship.addressee != requesting_user:
            raise ValueError("You are not part of this friendship")

        # Validate friendship is accepted
        if friendship.status != 'accepted':
            raise ValueError("Cannot remove a non-accepted friendship")

        # Delete the friendship (no notification for unfriending)
        friendship.delete()

    @staticmethod
    def get_friends(user: User):
        """Get all accepted friends for user with proper blocking enforcement."""
        return Friendship.get_friends(user)

    @staticmethod
    def get_pending_requests(user: User):
        """Get pending friend requests received by user."""
        # Clean up expired requests first
        expiry_date = timezone.now() - timedelta(days=FriendshipService.REQUEST_EXPIRY_DAYS)
        Friendship.objects.filter(
            addressee=user,
            status='pending',
            created_at__lt=expiry_date
        ).delete()

        # Get pending requests, excluding blocked users
        blocked_users = Block.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker', 'blocked')

        blocked_ids = set()
        for blocker_id, blocked_id in blocked_users:
            if blocker_id == user.id:
                blocked_ids.add(blocked_id)
            else:
                blocked_ids.add(blocker_id)

        return Friendship.objects.filter(
            addressee=user,
            status='pending'
        ).exclude(
            requester_id__in=blocked_ids
        ).select_related('requester', 'addressee')

    @staticmethod
    def get_sent_requests(user: User):
        """Get pending friend requests sent by user."""
        # Clean up expired requests first
        expiry_date = timezone.now() - timedelta(days=FriendshipService.REQUEST_EXPIRY_DAYS)
        Friendship.objects.filter(
            requester=user,
            status='pending',
            created_at__lt=expiry_date
        ).delete()

        # Get sent requests, excluding blocked users
        blocked_users = Block.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker', 'blocked')

        blocked_ids = set()
        for blocker_id, blocked_id in blocked_users:
            if blocker_id == user.id:
                blocked_ids.add(blocked_id)
            else:
                blocked_ids.add(blocker_id)

        return Friendship.objects.filter(
            requester=user,
            status='pending'
        ).exclude(
            addressee_id__in=blocked_ids
        ).select_related('requester', 'addressee')

    @staticmethod
    def suggest_friends(user: User, limit: int = 10) -> List[dict]:
        """
        Suggest friends based on:
        - Users from completed climbing sessions
        - Mutual friends (friends of friends)
        - Users with similar destinations/disciplines
        Exclude: existing friends, pending requests, blocked users
        """
        from climbing_sessions.models import Session
        from trips.models import Trip, Destination

        suggestions = []

        # Get current friends and pending requests
        friend_query = Friendship.objects.filter(
            Q(requester=user, status='accepted') |
            Q(addressee=user, status='accepted') |
            Q(requester=user, status='pending') |
            Q(addressee=user, status='pending')
        )
        current_friend_ids = set()
        for f in friend_query:
            current_friend_ids.add(f.requester_id)
            current_friend_ids.add(f.addressee_id)

        # Remove user's own ID
        current_friend_ids.discard(user.id)

        # Get blocked user IDs (bilateral)
        blocked_ids = set()
        blocked_users = Block.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker', 'blocked')

        for blocker_id, blocked_id in blocked_users:
            if blocker_id == user.id:
                blocked_ids.add(blocked_id)
            else:
                blocked_ids.add(blocker_id)

        exclude_ids = current_friend_ids | blocked_ids | {user.id}

        # 1. Users from completed climbing sessions
        # Find users who have been in completed sessions with this user
        completed_sessions = Session.objects.filter(
            Q(inviter=user) | Q(invitee=user),
            status='completed'
        )

        session_partner_ids = set()
        for session in completed_sessions:
            if session.inviter_id == user.id:
                session_partner_ids.add(session.invitee_id)
            else:
                session_partner_ids.add(session.inviter_id)

        session_partner_ids -= exclude_ids

        # Count sessions per partner
        session_counts = {}
        for session in completed_sessions:
            partner_id = session.invitee_id if session.inviter_id == user.id else session.inviter_id
            if partner_id not in exclude_ids:
                session_counts[partner_id] = session_counts.get(partner_id, 0) + 1

        session_partners = User.objects.visible_to(user).filter(
            id__in=session_partner_ids
        )[:5]

        for partner in session_partners:
            count = session_counts.get(partner.id, 1)
            suggestions.append({
                'user': partner,
                'reason': f'Climbed together {count} time(s)',
                'mutual_friends_count': 0,
                'priority': 1
            })

        # 2. Mutual friends (friends of friends)
        friend_ids = set(Friendship.get_friends(user).values_list('id', flat=True))

        if friend_ids:
            mutual_suggestions = User.objects.visible_to(user).filter(
                Q(friendship_requests_received__requester_id__in=friend_ids,
                  friendship_requests_received__status='accepted') |
                Q(friendship_requests_sent__addressee_id__in=friend_ids,
                  friendship_requests_sent__status='accepted')
            ).exclude(
                id__in=exclude_ids
            ).annotate(
                mutual_count=Count('id')
            ).order_by('-mutual_count')[:5]

            for suggestion in mutual_suggestions:
                # Calculate actual mutual friend count
                mutual_friends = Friendship.objects.filter(
                    Q(requester=suggestion, addressee__in=friend_ids, status='accepted') |
                    Q(addressee=suggestion, requester__in=friend_ids, status='accepted')
                ).count()

                suggestions.append({
                    'user': suggestion,
                    'reason': f'{mutual_friends} mutual friend(s)',
                    'mutual_friends_count': mutual_friends,
                    'priority': 2
                })

        # 3. Users with similar destinations/disciplines
        user_destinations = Trip.objects.filter(
            user=user
        ).values_list('destination_id', flat=True).distinct()

        user_disciplines = user.disciplines.values_list('discipline', flat=True)

        if user_destinations or user_disciplines:
            similar_users = User.objects.visible_to(user).filter(
                Q(trips__destination_id__in=user_destinations) |
                Q(disciplines__discipline__in=user_disciplines)
            ).exclude(
                id__in=exclude_ids | set([s['user'].id for s in suggestions])
            ).annotate(
                similarity_score=Count('id')
            ).order_by('-similarity_score')[:5]

            for similar_user in similar_users:
                suggestions.append({
                    'user': similar_user,
                    'reason': 'Similar climbing interests',
                    'mutual_friends_count': 0,
                    'priority': 3
                })

        # Sort by priority and limit
        suggestions.sort(key=lambda x: (x['priority'], -x['mutual_friends_count']))

        return suggestions[:limit]