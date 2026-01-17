# Notification System Component Hierarchy

## Visual Structure

```
RootLayout (app/layout.tsx)
│
├── NotificationPopup (global, shows critical notifications)
│   └── Framer Motion AnimatePresence
│       └── Modal with overlay
│           ├── Close button
│           ├── Icon (based on type)
│           ├── User avatar (if available)
│           ├── Title & Message
│           ├── Match score badge (for matches)
│           ├── Trip details (if available)
│           └── Action buttons (View / Dismiss)
│
└── Navigation
    └── NotificationBell
        ├── Bell Icon (heroicons)
        ├── Badge (red, shows unread count)
        └── NotificationDropdown (toggles on click)
            ├── Header ("Notifications", "Mark all as read")
            ├── Notification List (5 most recent)
            │   └── NotificationItem (×5)
            │       ├── Icon (dynamic based on type)
            │       ├── Title & Message
            │       ├── Time ago
            │       └── Unread indicator (dot)
            └── Footer ("View All Notifications")

NotificationsPage (app/notifications/page.tsx)
├── Header (title, description)
├── Actions Bar
│   ├── Filter Tabs (All, Matches, Connections, Sessions)
│   └── Action Buttons (Mark all as read, Clear read)
└── Grouped Notification Lists
    ├── Today
    │   └── NotificationItem (×N)
    ├── Yesterday
    │   └── NotificationItem (×N)
    ├── This Week
    │   └── NotificationItem (×N)
    └── Older
        └── NotificationItem (×N)
```

## Data Flow

```
User Login
    ↓
NotificationBell mounts
    ↓
notificationStore.startPolling()
    ↓
API: GET /api/notifications/unread_count/
    ↓
Update badge count
    ↓
API: GET /api/notifications/ (limit=20)
    ↓
Check for critical unread (popup_shown=false)
    ↓
If exists: Show NotificationPopup
    ↓
Poll every 30 seconds:
    - GET /api/notifications/unread_count/
    - GET /api/notifications/
    - Update UI if changes detected
```

## State Management Flow

```
notificationStore (Zustand)
├── notifications: Notification[]
├── unreadCount: number
├── currentPopup: Notification | null
├── showPopup: boolean
├── isPolling: boolean
└── pollInterval: NodeJS.Timeout | null

Actions:
├── fetchNotifications()
│   └── Updates notifications[], checks for critical popups
├── fetchUnreadCount()
│   └── Updates unreadCount (badge)
├── markAsRead(id)
│   └── POST /api/notifications/{id}/mark_read/
├── markAllAsRead()
│   └── POST /api/notifications/mark_all_read/
├── dismissPopup()
│   └── POST /api/notifications/{id}/mark_popup_shown/
├── showNextPopup()
│   └── Find next critical unread notification
├── startPolling()
│   └── setInterval(30s)
└── stopPolling()
    └── clearInterval()
```

## Notification Types & Icons

| Type | Icon | Priority | Popup? |
|------|------|----------|--------|
| `new_match` | ✨ Sparkles | Critical | Yes |
| `connection_request` | 👥 Users | Critical | Yes |
| `connection_accepted` | 👥 Users | High | No |
| `connection_declined` | ❌ X-Circle | Medium | No |
| `session_invite` | 📅 Calendar | High | No |
| `session_update` | 📅 Calendar | Medium | No |

## Example Notification Objects

### New Match Notification
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "recipient": "user-123",
  "notification_type": "new_match",
  "priority": "critical",
  "title": "New climbing match!",
  "message": "Sarah matches your Red River Gorge trip with a 92% compatibility score!",
  "action_url": "/matches/trip-abc123",
  "metadata": {
    "user_id": "user-456",
    "user_display_name": "Sarah",
    "user_avatar": "https://example.com/avatars/sarah.jpg",
    "match_score": 92,
    "trip_destination": "Red River Gorge",
    "trip_dates": "March 15-20, 2026"
  },
  "is_read": false,
  "popup_shown": false,
  "created_at": "2026-01-16T10:30:00Z",
  "read_at": null
}
```

### Connection Request Notification
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "recipient": "user-123",
  "notification_type": "connection_request",
  "priority": "critical",
  "title": "New connection request",
  "message": "John wants to connect with you for climbing at Bishop",
  "action_url": "/sessions/session-xyz789",
  "metadata": {
    "user_id": "user-789",
    "user_display_name": "John",
    "user_avatar": "https://example.com/avatars/john.jpg",
    "trip_destination": "Bishop",
    "trip_dates": "April 1-5, 2026"
  },
  "is_read": false,
  "popup_shown": false,
  "created_at": "2026-01-16T11:45:00Z",
  "read_at": null
}
```

### Connection Accepted Notification
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "recipient": "user-123",
  "notification_type": "connection_accepted",
  "priority": "high",
  "title": "Connection accepted!",
  "message": "Emma accepted your connection request for Yosemite",
  "action_url": "/sessions/session-qwe456",
  "metadata": {
    "user_id": "user-321",
    "user_display_name": "Emma",
    "user_avatar": "https://example.com/avatars/emma.jpg",
    "trip_destination": "Yosemite National Park",
    "trip_dates": "May 10-15, 2026"
  },
  "is_read": false,
  "popup_shown": true,
  "created_at": "2026-01-16T12:15:00Z",
  "read_at": null
}
```

### Session Invite Notification
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "recipient": "user-123",
  "notification_type": "session_invite",
  "priority": "high",
  "title": "Session invite",
  "message": "Mike invited you to climb on March 16 (afternoon)",
  "action_url": "/sessions/session-asd987",
  "metadata": {
    "user_id": "user-654",
    "user_display_name": "Mike",
    "session_id": "session-asd987",
    "trip_destination": "Smith Rock",
    "trip_dates": "March 16, 2026"
  },
  "is_read": true,
  "popup_shown": true,
  "created_at": "2026-01-15T14:20:00Z",
  "read_at": "2026-01-15T15:30:00Z"
}
```

## Responsive Breakpoints

### Mobile (< 768px)
- Bell icon: Always visible in header
- Dropdown: Full width with `max-w-[calc(100vw-2rem)]`
- Popup: Full-screen overlay
- Notification page: Single column, stacked filters

### Tablet (768px - 1024px)
- Bell icon: In header with some spacing
- Dropdown: 384px width (96 * 4)
- Popup: Centered modal, max-width 500px
- Notification page: Side-by-side filters

### Desktop (> 1024px)
- Bell icon: Between nav links and user profile
- Dropdown: Positioned absolute right
- Popup: Centered modal with backdrop blur
- Notification page: Full layout with all features

## Accessibility Tree

```
Navigation
├── Link: "Send Buddy"
├── Navigation Links
├── Button: "Notifications, 5 unread" [expanded=false] [haspopup=dialog]
│   ├── SVG: Bell icon [hidden from screen readers]
│   └── Span: "99+" [aria-hidden=true]
├── Text: User name
└── Button: "Logout"

When dropdown open:
└── Dialog: "Notifications"
    ├── Heading: "Notifications"
    ├── Button: "Mark all as read"
    ├── List
    │   ├── Button: [notification content] [role=button]
    │   └── ...
    └── Link: "View All Notifications"

Popup Modal:
└── Dialog: [role=dialog] [labelledby=notification-popup-title] [describedby=notification-popup-message]
    ├── Button: "Close notification" [aria-label]
    ├── Heading: [id=notification-popup-title]
    ├── Paragraph: [id=notification-popup-message]
    ├── Button: "View Match"
    └── Button: "Dismiss"
```

## Performance Characteristics

### Initial Load
- Notification store: 0ms (lazy initialization)
- First poll: ~200-500ms (API call)
- Badge render: < 16ms (single frame)
- Dropdown render: < 16ms (on-demand)

### Polling Overhead
- Frequency: Every 30 seconds
- Payload size: ~2-5KB (for 20 notifications)
- Network requests: 2 per poll (count + list)
- CPU usage: Minimal (< 1% on modern devices)

### Memory Usage
- Notification store: ~5-10KB (20 notifications)
- Component tree: ~2-3KB (when mounted)
- Total overhead: < 15KB in memory

### Optimization Opportunities
1. Debounce polling if user is idle (no activity for 5 minutes)
2. Use Web Workers for background polling
3. Implement service worker for offline support
4. Add pagination for notifications > 100

## Error Scenarios & Handling

| Scenario | Behavior |
|----------|----------|
| API endpoint not found (404) | Silent fail, log error, show empty state |
| Network timeout | Retry once, then show empty state |
| Invalid auth token | Stop polling, trigger logout |
| Malformed response | Log error, skip that notification |
| Backend down | Show empty state, keep polling (retry) |
| User logs out | Stop polling immediately, clear state |
| Browser tab hidden | Continue polling (user may switch back) |
| Browser offline | Pause polling until online |

## Future Enhancements Roadmap

### Phase 2: Real-Time (Q2 2026)
- [ ] WebSocket connection for instant delivery
- [ ] Server-sent events (SSE) as fallback
- [ ] Optimistic UI updates

### Phase 3: Advanced Features (Q3 2026)
- [ ] Push notifications (browser API)
- [ ] Email notifications (digest)
- [ ] Notification preferences page
- [ ] Do Not Disturb mode

### Phase 4: Analytics (Q4 2026)
- [ ] Click-through rate tracking
- [ ] Time-to-action metrics
- [ ] A/B testing framework
- [ ] User engagement scoring

---

**Last Updated:** January 16, 2026
**Status:** ✅ Phase 1 Complete
**Next Review:** After backend implementation
