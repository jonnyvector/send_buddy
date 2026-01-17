# Notification API Quick Reference

## Base URL
All endpoints: `http://localhost:8000/api/notifications/`

## Authentication
All endpoints require JWT token:
```
Authorization: Bearer <access_token>
```

## Endpoints Summary

| Method | Endpoint | Description | Use Case |
|--------|----------|-------------|----------|
| GET | `/notifications/` | List all notifications (paginated) | Notification center page |
| GET | `/notifications/unread/` | Get unread notifications | Bell dropdown (recent 5) |
| GET | `/notifications/unread-count/` | Get count only | Badge number (polling) |
| POST | `/notifications/{id}/mark-read/` | Mark single as read | User clicks notification |
| POST | `/notifications/mark-all-read/` | Mark all as read | "Mark all as read" button |
| POST | `/notifications/{id}/mark-popup-shown/` | Track popup display | After showing popup modal |
| DELETE | `/notifications/{id}/` | Delete notification | User dismisses notification |

## Common Query Parameters

### List Notifications (`GET /notifications/`)
- `?read=false` - Filter unread only
- `?read=true` - Filter read only
- `?type=new_match` - Filter by notification type
- `?page=2` - Pagination (page number)
- `?page_size=20` - Items per page (default: 20, max: 100)

### Unread Notifications (`GET /notifications/unread/`)
- `?limit=5` - Limit number of results

## Response Examples

### List Response (Paginated)
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/notifications/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "recipient": { "id": "uuid", "display_name": "...", "avatar": "..." },
      "notification_type": "new_match",
      "notification_type_display": "New Match",
      "priority": "critical",
      "priority_display": "Critical",
      "title": "New Match: Jane Doe",
      "message": "You've been matched with Jane Doe...",
      "action_url": "/matches/abc/detail/xyz",
      "is_read": false,
      "popup_shown": false,
      "created_at": "2026-01-16T00:00:00Z",
      "read_at": null,
      "related_user": { "id": "uuid", "display_name": "...", "avatar": "..." },
      "related_trip": { "id": "uuid", "destination": "...", "start_date": "...", "end_date": "..." }
    }
  ]
}
```

### Unread Count Response
```json
{
  "count": 3
}
```

### Mark All Read Response
```json
{
  "detail": "Marked 3 notifications as read",
  "count": 3
}
```

## Notification Types

| Type | Description | Priority | Popup? |
|------|-------------|----------|--------|
| `new_match` | New climbing partner match found | critical | ✅ Yes |
| `connection_request` | Someone wants to connect (Phase 2) | critical | ✅ Yes |
| `connection_accepted` | Your connection request was accepted (Phase 2) | high | ❌ No |
| `connection_declined` | Your connection request was declined (Phase 2) | medium | ❌ No |
| `session_invite` | Invited to climbing session (Phase 2) | high | ❌ No |
| `session_update` | Session details changed (Phase 2) | medium | ❌ No |

## Priority Levels

| Priority | Badge | Sound | Popup | Use Case |
|----------|-------|-------|-------|----------|
| `critical` | ✅ | ✅ | ✅ | Must-see events (matches, connection requests) |
| `high` | ✅ | ✅ | ❌ | Important events (accepted connections) |
| `medium` | ✅ | ❌ | ❌ | Informational events (declined requests) |

## Frontend Integration Examples

### 1. Bell Icon Badge (Polling Every 30s)
```javascript
async function updateBadge() {
  const res = await fetch('/api/notifications/unread-count/', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const { count } = await res.json();
  setBadgeCount(count);
}

setInterval(updateBadge, 30000);
```

### 2. Show Popup Modal on Login
```javascript
async function checkForPopups() {
  const res = await fetch('/api/notifications/unread/', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const { results } = await res.json();

  const unshownCritical = results.find(
    n => n.priority === 'critical' && !n.popup_shown
  );

  if (unshownCritical) {
    showPopup(unshownCritical);

    // Mark as shown
    await fetch(`/api/notifications/${unshownCritical.id}/mark-popup-shown/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
  }
}
```

### 3. Bell Dropdown (Show Recent 5)
```javascript
async function showDropdown() {
  const res = await fetch('/api/notifications/?page_size=5', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const { results } = await res.json();
  renderDropdown(results);
}
```

### 4. Notification Center Page (All Notifications)
```javascript
async function loadNotifications(page = 1) {
  const res = await fetch(`/api/notifications/?page=${page}&page_size=20`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  renderNotifications(data.results);
  renderPagination(data.count, page);
}
```

### 5. Click Notification → Mark Read + Navigate
```javascript
async function handleClick(notification) {
  // Mark as read
  await fetch(`/api/notifications/${notification.id}/mark-read/`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });

  // Navigate to action URL
  navigate(notification.action_url);
}
```

### 6. Mark All as Read Button
```javascript
async function markAllRead() {
  await fetch('/api/notifications/mark-all-read/', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  refreshNotifications();
}
```

### 7. Delete Notification (Dismiss)
```javascript
async function deleteNotification(id) {
  await fetch(`/api/notifications/${id}/`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  removeFromUI(id);
}
```

## Rate Limits
- GET endpoints: 60 requests/minute per user
- POST/DELETE endpoints: Default DRF limits

## Error Responses

### 401 Unauthorized (No token or expired)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden (Wrong user)
```json
{
  "detail": "Not authorized to modify this notification"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

## Testing with cURL

### Get Unread Count
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/notifications/unread-count/
```

### List Unread Notifications
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/notifications/?read=false"
```

### Mark Notification as Read
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/notifications/<id>/mark-read/
```

### Mark All as Read
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/notifications/mark-all-read/
```

### Delete Notification
```bash
curl -X DELETE \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/notifications/<id>/
```

## Notes
- All UUIDs are formatted as strings in JSON
- Timestamps are ISO 8601 format (UTC)
- Avatar URLs are relative paths (prepend MEDIA_URL)
- action_url is a frontend route (e.g., `/matches/123/detail/456`)
- Notifications are ordered by created_at (newest first)
- Pagination follows DRF standard (count, next, previous, results)
