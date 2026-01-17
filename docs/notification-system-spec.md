# Notification System Specification

## Overview
Implement a Tinder-style notification system that prominently alerts users about important events (new matches, connection requests, etc.).

## Core Features

### 1. Notification Types
- **New Match Available**: When someone creates a trip that matches yours
- **Connection Request**: When someone wants to connect with you
- **Connection Accepted**: When your connection request is accepted
- **Connection Declined**: When your connection request is declined
- **Session Updates**: Session invites, confirmations, changes

### 2. Notification Display

#### Header Bell Icon
- Bell icon in navigation header (always visible when authenticated)
- Red badge with count of unread notifications
- Clicking opens dropdown notification list
- Max 5 most recent in dropdown, "View All" link to full page

#### Popup Modal (Tinder-style)
- Large, eye-catching modal for high-priority notifications (new matches, connection requests)
- Shows immediately when user logs in or when notification arrives
- Displays:
  - User photo/avatar
  - Match score (for matches)
  - Trip details (destination, dates)
  - Quick action buttons (View Match, Connect, Dismiss)
- Can be dismissed but notification persists in bell icon
- Only shows once per notification

#### Notification Center Page
- Dedicated `/notifications` page
- List of all notifications (read and unread)
- Grouped by date (Today, Yesterday, This Week, Older)
- Filter by type
- Mark as read/unread
- Clear all read notifications

### 3. When Notifications Are Created

#### Backend Triggers (Django Signals)
```python
# Post-save signal on Trip model
@receiver(post_save, sender=Trip)
def notify_matching_users(sender, instance, created, **kwargs):
    """When a trip is created, find matching users and notify them"""
    if created and instance.is_active:
        # Run matching algorithm
        # Create notifications for top matches
        pass

# Post-save signal on Connection model
@receiver(post_save, sender=Connection)
def notify_connection_status(sender, instance, created, **kwargs):
    """Notify users about connection requests/updates"""
    if created:
        # Notify recipient about new request
        pass
    elif instance.status_changed:
        # Notify requester about acceptance/decline
        pass
```

#### Notification Priorities
- **Critical** (show popup): New matches, connection requests
- **High** (badge only): Connection accepted, session invites
- **Medium** (badge only): Session updates, connection declined

### 4. Backend Implementation

#### Models
```python
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_match', 'New Match'),
        ('connection_request', 'Connection Request'),
        ('connection_accepted', 'Connection Accepted'),
        ('connection_declined', 'Connection Declined'),
        ('session_invite', 'Session Invite'),
    ]

    PRIORITY_LEVELS = [
        ('critical', 'Critical'),  # Show popup
        ('high', 'High'),          # Badge + sound
        ('medium', 'Medium'),      # Badge only
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')

    # Generic relation to any model (Trip, Connection, Session, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Notification content
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_url = models.CharField(max_length=255, blank=True)  # Where to redirect on click

    # Metadata
    is_read = models.BooleanField(default=False)
    popup_shown = models.BooleanField(default=False)  # Track if popup was displayed
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
        ]
```

#### API Endpoints
```
GET /api/notifications/                 # List all notifications (paginated)
GET /api/notifications/unread/          # Get unread notifications
GET /api/notifications/unread_count/    # Get count of unread
POST /api/notifications/{id}/mark_read/ # Mark single as read
POST /api/notifications/mark_all_read/  # Mark all as read
DELETE /api/notifications/{id}/         # Delete single notification
```

#### Services
```python
class NotificationService:
    @staticmethod
    def create_new_match_notification(recipient: User, match: Dict):
        """Create notification when a new match is found"""
        pass

    @staticmethod
    def create_connection_request_notification(recipient: User, connection: Connection):
        """Create notification for connection request"""
        pass

    @staticmethod
    def get_unread_notifications(user: User, limit=None):
        """Get unread notifications for user"""
        pass

    @staticmethod
    def mark_popup_shown(notification_id: str):
        """Mark that popup was shown to user"""
        pass
```

### 5. Frontend Implementation

#### Components
```
components/
  notifications/
    NotificationBell.tsx          # Header bell icon with badge
    NotificationDropdown.tsx      # Dropdown from bell icon
    NotificationPopup.tsx         # Full-screen modal for critical notifications
    NotificationList.tsx          # List view for notification center
    NotificationItem.tsx          # Single notification card
```

#### State Management
```typescript
// Add to authStore or create notificationStore
interface NotificationStore {
  notifications: Notification[];
  unreadCount: number;
  showPopup: boolean;
  currentPopup: Notification | null;

  fetchNotifications: () => Promise<void>;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  dismissPopup: () => void;
}
```

#### Polling Strategy
- Poll for new notifications every 30 seconds when user is active
- Show popup immediately when new critical notification detected
- Update badge count in real-time
- Optional: Use WebSockets for instant delivery (Phase 2)

### 6. User Experience Flow

#### Login Flow
1. User logs in
2. Fetch unread notifications
3. If critical notifications exist (popup_shown=false):
   - Show popup modal with notification
   - Mark popup_shown=true
   - User can dismiss or take action
4. Badge shows total unread count

#### Active User Flow
1. Poll every 30 seconds
2. If new notification arrives:
   - Update badge count
   - If critical priority: show popup
   - Play subtle notification sound (optional)
3. User clicks bell → dropdown shows recent 5
4. User clicks "View All" → navigate to notification center

#### Notification Center
1. Shows all notifications grouped by date
2. Can filter by type (Matches, Connections, Sessions)
3. Click notification → mark as read + navigate to related page
4. "Clear all read" button

### 7. Design Specs

#### Colors (using existing design system)
- Unread: emerald-400 background with emerald-950 text
- Read: stone-50 background with stone-600 text
- Badge: red-500 background with white text
- Popup overlay: black with 50% opacity

#### Popup Modal
- Full-screen overlay with centered modal
- Max width: 500px
- Padding: 32px
- Border radius: 24px (rounded-3xl)
- Shadow: large drop shadow
- Animation: Scale up + fade in (200ms)

#### Bell Icon
- Size: 24px
- Badge: 18px circle, positioned top-right
- Badge max number: 99 (show "99+" for more)
- Hover: emerald-400 background
- Active: emerald-600 background

### 8. Implementation Phases

#### Phase 1: Core Infrastructure (MVP)
- [ ] Backend: Notification model + signals
- [ ] Backend: API endpoints
- [ ] Frontend: NotificationBell component
- [ ] Frontend: NotificationPopup component
- [ ] New match notifications only

#### Phase 2: Full Feature Set
- [ ] Connection request notifications
- [ ] Connection accepted/declined notifications
- [ ] Notification center page
- [ ] Mark as read functionality
- [ ] Filtering and search

#### Phase 3: Enhancements
- [ ] WebSocket support for real-time
- [ ] Push notifications (browser)
- [ ] Email notifications (digest)
- [ ] Notification preferences/settings

## Open Questions
1. Should we play a sound when notification arrives?
2. How long should we keep read notifications? (30 days? 90 days?)
3. Should users be able to mute certain notification types?
4. Do we need a "Do Not Disturb" mode?

## Success Metrics
- Users check notifications within 1 hour of creation
- 80%+ of connection requests come from notification clicks
- Reduced time between match creation and first connection
