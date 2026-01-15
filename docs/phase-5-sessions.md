# Phase 5: Sessions & Messaging

## Overview
Implement session-based invitations and chat system. This allows users to invite matches to climb together and coordinate logistics.

## Dependencies
- Phase 1 (Session/Message models) ✓
- Phase 2 (Authentication) ✓
- Phase 4 (Matching) ✓

---

## 1. Session-Based Communication Philosophy

**Key Concept:** Unlike open DMs, all conversations are **tied to a specific climbing session** (date + time + location).

**Benefits:**
- Keeps conversations focused
- Reduces awkward "hey wanna climb sometime?" open-ended chats
- Clear call-to-action (accept/decline invitation)
- Safety: all sessions have context (when, where, what)

**Flow:**
1. User A finds User B in match feed
2. User A sends invitation: "Climb at [Crag] on [Date] [Time]"
3. User B receives notification
4. User B accepts → both can chat within the session
5. After session date, both prompted for feedback

---

## 2. Backend API Endpoints

### 2.1 Send Invitation

**POST `/api/sessions/`**

Request:
```json
{
  "invitee_id": "uuid",
  "trip_id": "uuid",
  "proposed_date": "2026-03-16",
  "time_block": "morning",
  "crag": "Thaiwand Wall",
  "goal": "Work on 5.11 endurance routes"
}
```

Response (201):
```json
{
  "id": "session-uuid",
  "inviter": {
    "id": "uuid",
    "display_name": "Alex Climber",
    "avatar": "https://..."
  },
  "invitee": {
    "id": "uuid",
    "display_name": "Sarah Climbs",
    "avatar": "https://..."
  },
  "trip": {
    "id": "uuid",
    "destination": {
      "slug": "railay",
      "name": "Railay, Krabi"
    },
    "start_date": "2026-03-15",
    "end_date": "2026-03-28"
  },
  "proposed_date": "2026-03-16",
  "time_block": "morning",
  "crag": "Thaiwand Wall",
  "goal": "Work on 5.11 endurance routes",
  "status": "pending",
  "created_at": "2026-01-13T12:00:00Z",
  "messages": []
}
```

**Validation:**
- invitee must exist
- proposed_date must be within trip date range
- Cannot send duplicate invitation (same inviter + invitee + proposed_date)
- Cannot invite yourself

**Rate Limiting:**
- 10 session invitations per hour per user

**Side Effects:**
- Send push notification to invitee (TODO: Phase 6+)
- Send email notification if enabled (TODO: Phase 6+)

**Note:** Blocking validation will be added in Phase 6 (Trust & Safety)

**Error Responses:**

400 Bad Request:
```json
{
  "detail": "Proposed date must be within trip date range"
}
```

400 Bad Request (duplicate):
```json
{
  "detail": "You already have a pending invitation with this user for this date"
}
```

404 Not Found:
```json
{
  "detail": "Invitee not found"
}
```

404 Not Found (trip):
```json
{
  "detail": "Trip not found"
}
```

---

### 2.2 List My Sessions

**GET `/api/sessions/`**

Query params:
- `status` (pending, accepted, declined, cancelled, completed)
- `role` (inviter, invitee) - filter by user's role

Response (200):
```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid",
      "inviter": { ... },
      "invitee": { ... },
      "trip": { ... },
      "proposed_date": "2026-03-16",
      "time_block": "morning",
      "crag": "Thaiwand Wall",
      "goal": "...",
      "status": "accepted",
      "created_at": "2026-01-13T12:00:00Z",
      "last_message_at": "2026-01-14T09:30:00Z"
    }
  ]
}
```

**Ordering:**
- Pending first
- Then by last_message_at desc

---

### 2.3 Get Session Detail

**GET `/api/sessions/:id/`**

Response (200):
```json
{
  "id": "uuid",
  "inviter": { ...full profile... },
  "invitee": { ...full profile... },
  "trip": { ... },
  "proposed_date": "2026-03-16",
  "time_block": "morning",
  "crag": "Thaiwand Wall",
  "goal": "Work on 5.11 endurance routes",
  "status": "accepted",
  "created_at": "2026-01-13T12:00:00Z",
  "updated_at": "2026-01-14T09:30:00Z",
  "last_message_at": "2026-01-14T09:30:00Z",
  "messages": [
    {
      "id": "uuid",
      "sender": {
        "id": "uuid",
        "display_name": "Alex Climber"
      },
      "body": "Hey! Looking forward to climbing together!",
      "created_at": "2026-01-13T12:05:00Z"
    },
    {
      "id": "uuid",
      "sender": {
        "id": "uuid",
        "display_name": "Sarah Climbs"
      },
      "body": "Me too! I'll bring my rope and quickdraws.",
      "created_at": "2026-01-14T09:30:00Z"
    }
  ]
}
```

**Permissions:**
- Only inviter or invitee can view

---

### 2.4 Accept Invitation

**POST `/api/sessions/:id/accept/`**

Response (200):
```json
{
  "id": "uuid",
  "status": "accepted",
  "message": "Invitation accepted"
}
```

**Permissions:**
- Only invitee can accept
- Session must be in 'pending' status

**Side Effects:**
- Update status to 'accepted'
- Send notification to inviter

---

### 2.5 Decline Invitation

**POST `/api/sessions/:id/decline/`**

Request (optional):
```json
{
  "message": "Sorry, I have other plans that day."
}
```

Response (200):
```json
{
  "id": "uuid",
  "status": "declined",
  "message": "Invitation declined"
}
```

**Permissions:**
- Only invitee can decline

**Side Effects:**
- Update status to 'declined'
- Optionally add message as first chat message
- Send notification to inviter

---

### 2.6 Cancel Session

**POST `/api/sessions/:id/cancel/`**

Request (optional):
```json
{
  "reason": "Weather looks bad, let's reschedule."
}
```

Response (200):
```json
{
  "id": "uuid",
  "status": "cancelled",
  "message": "Session cancelled"
}
```

**Permissions:**
- Either inviter or invitee can cancel

**Side Effects:**
- Update status to 'cancelled'
- Send notification to other party

---

### 2.7 Mark Session as Completed

**POST `/api/sessions/:id/complete/`**

Response (200):
```json
{
  "id": "uuid",
  "status": "completed",
  "message": "Session marked as completed. Please provide feedback."
}
```

**Permissions:**
- Either party can mark as completed
- Or auto-complete 24h after proposed_date

**Side Effects:**
- Update status to 'completed'
- Prompt both users for feedback (Phase 6)

---

### 2.8 Send Message

**POST `/api/sessions/:id/messages/`**

Request:
```json
{
  "body": "See you at 8am at the parking lot!"
}
```

Response (201):
```json
{
  "id": "uuid",
  "session": "session-uuid",
  "sender": {
    "id": "uuid",
    "display_name": "Alex Climber"
  },
  "body": "See you at 8am at the parking lot!",
  "created_at": "2026-03-15T18:00:00Z"
}
```

**Validation:**
- body max 2000 chars
- Session must be in 'accepted' or 'pending' status
- Sender must be inviter or invitee

**Rate Limiting:**
- 100 messages per hour per user

**Side Effects:**
- Update session.last_message_at
- Send notification to other party (TODO: Phase 6+)

---

### 2.9 Get Messages for Session

**GET `/api/sessions/:id/messages/`**

Response (200):
```json
{
  "count": 15,
  "results": [
    {
      "id": "uuid",
      "sender": { ... },
      "body": "...",
      "created_at": "2026-01-13T12:05:00Z"
    }
  ]
}
```

**Ordering:** created_at ascending (oldest first)

---

### 2.10 Mark Messages as Read

**POST `/api/sessions/:id/mark-read/`**

Response (200):
```json
{
  "message": "Messages marked as read"
}
```

**Note:** Unread tracking will be implemented in a future phase. For now, this endpoint is a placeholder.

---

## 3. Real-Time Chat (MVP vs Phase 2)

### MVP Approach: REST Polling
- Frontend polls `/api/sessions/:id/messages/` every 5 seconds when chat is open
- Simple, no WebSocket infrastructure needed

### Phase 2: WebSockets
- Use Django Channels for real-time updates
- Subscribe to session-specific channels
- Instant message delivery

**Recommendation:** Start with polling for MVP, add WebSockets later.

---

## 4. Frontend Implementation

### 4.1 Pages & Routes

#### `/sessions` - Session List
- Tabs: Pending / Accepted / Past
- Each session card:
  - Other user's avatar + name
  - Session details (date, time, crag)
  - Status badge
  - Last message preview
  - Unread count badge
- Click → `/sessions/:id`

#### `/sessions/:id` - Session Detail / Chat
- Header:
  - Other user's profile summary
  - Session details (date, time, crag, goal)
  - Status badge
  - Actions: Accept / Decline / Cancel (depending on status + role)
- Chat area:
  - Message list (scrollable)
  - Message input (if status = accepted or pending)
  - "Mark as Completed" button (if date has passed)

#### Modal: Send Invitation
- Triggered from match feed ("Send Invite" button)
- Form fields:
  - Date (date picker, limited to trip date range)
  - Time block (radio: Morning / Afternoon / Full Day)
  - Crag (text input, optional)
  - Goal (textarea, optional)
- "Send Invitation" button

---

### 4.2 Components

#### `SessionCard`
```typescript
interface SessionCardProps {
  session: Session;
  onClick: () => void;
}

// Displays:
// - Other user's avatar + name
// - Date + time + crag
// - Status badge
// - Last message preview (truncated)
// - Unread badge
```

#### `SessionHeader`
```typescript
interface SessionHeaderProps {
  session: Session;
  currentUserId: string;
  onAccept: () => void;
  onDecline: () => void;
  onCancel: () => void;
  onComplete: () => void;
}

// Displays:
// - User profile summary
// - Session details
// - Action buttons based on status + role
```

#### `MessageList`
```typescript
interface MessageListProps {
  messages: Message[];
  currentUserId: string;
}

// Chat bubble UI:
// - Own messages aligned right (blue)
// - Other's messages aligned left (gray)
// - Timestamps
```

#### `MessageInput`
```typescript
interface MessageInputProps {
  onSend: (body: string) => Promise<void>;
  disabled: boolean;
}

// Text input + Send button
// Enter to send
// Disabled if session not accepted
```

#### `InviteModal`
```typescript
interface InviteModalProps {
  recipientUser: User;
  trip: Trip;
  onSend: (invitation: InvitationData) => Promise<void>;
  onClose: () => void;
}

// Form to create invitation
```

---

### 4.3 State Management

```typescript
// lib/sessions.ts

interface Session {
  id: string;
  inviter: User;
  invitee: User;
  trip: Trip;
  proposed_date: string;
  time_block: 'morning' | 'afternoon' | 'full_day';
  crag: string;
  goal: string;
  status: 'pending' | 'accepted' | 'declined' | 'cancelled' | 'completed';
  created_at: string;
  last_message_at: string | null;
  messages: Message[];
}

interface Message {
  id: string;
  session: string;
  sender: User;
  body: string;
  created_at: string;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSession: null,
  isLoading: false,

  fetchSessions: async () => { ... },
  fetchSessionDetail: async (id: string) => { ... },
  sendInvitation: async (data: InvitationData) => { ... },
  acceptSession: async (id: string) => { ... },
  declineSession: async (id: string, message?: string) => { ... },
  cancelSession: async (id: string, reason?: string) => { ... },
  completeSession: async (id: string) => { ... },
  sendMessage: async (sessionId: string, body: string) => { ... },
  markAsRead: async (sessionId: string) => { ... },

  // Polling for messages
  startPolling: (sessionId: string) => {
    const interval = setInterval(() => {
      get().fetchSessionDetail(sessionId);
    }, 5000);
    return interval;
  },

  stopPolling: (intervalId: number) => {
    clearInterval(intervalId);
  },
}));
```

---

## 5. Backend Implementation Details

### 5.1 Serializers

```python
# climbing_sessions/serializers.py

from rest_framework import serializers
from .models import Session, Message, SessionStatus
from trips.models import Trip, TimeBlock
from users.models import User
from users.serializers import UserSerializer
from trips.serializers import TripSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'session', 'sender', 'body', 'created_at']
        read_only_fields = ['id', 'session', 'sender', 'created_at']

class SessionSerializer(serializers.ModelSerializer):
    inviter = UserSerializer(read_only=True)
    invitee = UserSerializer(read_only=True)
    trip = TripSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Session
        fields = [
            'id', 'inviter', 'invitee', 'trip', 'proposed_date',
            'time_block', 'crag', 'goal', 'status', 'created_at',
            'updated_at', 'last_message_at', 'messages'
        ]
        read_only_fields = ['id', 'inviter', 'status', 'created_at', 'updated_at', 'last_message_at']

class CreateSessionSerializer(serializers.Serializer):
    invitee_id = serializers.UUIDField()
    trip_id = serializers.UUIDField()
    proposed_date = serializers.DateField()
    time_block = serializers.ChoiceField(choices=TimeBlock.choices)
    crag = serializers.CharField(max_length=200, required=False, allow_blank=True)
    goal = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate(self, data):
        user = self.context['request'].user

        # Check if invitee exists
        try:
            invitee = User.objects.get(id=data['invitee_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({"invitee_id": "Invitee not found"})

        # Prevent self-invites
        if invitee == user:
            raise serializers.ValidationError("Cannot invite yourself")

        # TODO: Check if blocked (Phase 6: Trust & Safety)
        # if Block.objects.filter(blocker=user, blocked=invitee).exists():
        #     raise serializers.ValidationError("Cannot invite blocked user")
        # if Block.objects.filter(blocker=invitee, blocked=user).exists():
        #     raise serializers.ValidationError("You have been blocked by this user")

        # Check trip ownership and date range
        try:
            trip = Trip.objects.get(id=data['trip_id'], user=user)
        except Trip.DoesNotExist:
            raise serializers.ValidationError({"trip_id": "Trip not found"})

        if not (trip.start_date <= data['proposed_date'] <= trip.end_date):
            raise serializers.ValidationError({
                "proposed_date": f"Date must be within trip dates ({trip.start_date} to {trip.end_date})"
            })

        # Check for duplicate invitation
        duplicate = Session.objects.filter(
            inviter=user,
            invitee=invitee,
            proposed_date=data['proposed_date'],
            status__in=[SessionStatus.PENDING, SessionStatus.ACCEPTED]
        ).exists()

        if duplicate:
            raise serializers.ValidationError(
                "You already have a pending or accepted invitation with this user for this date"
            )

        data['invitee'] = invitee
        data['trip'] = trip

        return data
```

---

### 5.2 Views

```python
# climbing_sessions/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .models import Session, Message
from .serializers import SessionSerializer, CreateSessionSerializer, MessageSerializer

@method_decorator(ratelimit(key='user', rate='10/h', method='POST'), name='create')
@method_decorator(ratelimit(key='user', rate='100/h', method='POST'), name='messages')
class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Session.objects.filter(
            Q(inviter=self.request.user) | Q(invitee=self.request.user)
        )

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by role
        role_filter = self.request.query_params.get('role')
        if role_filter == 'inviter':
            queryset = queryset.filter(inviter=self.request.user)
        elif role_filter == 'invitee':
            queryset = queryset.filter(invitee=self.request.user)

        return queryset.order_by('-created_at')

    def create(self, request):
        """Send invitation"""
        serializer = CreateSessionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        session = Session.objects.create(
            inviter=request.user,
            invitee=serializer.validated_data['invitee'],
            trip=serializer.validated_data['trip'],
            proposed_date=serializer.validated_data['proposed_date'],
            time_block=serializer.validated_data['time_block'],
            crag=serializer.validated_data.get('crag', ''),
            goal=serializer.validated_data.get('goal', ''),
            status='pending'
        )

        # TODO: Send notification

        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept invitation"""
        session = self.get_object()

        if session.invitee != request.user:
            return Response({'error': 'Only invitee can accept'}, status=status.HTTP_403_FORBIDDEN)

        if session.status != 'pending':
            return Response({'error': 'Can only accept pending invitations'}, status=status.HTTP_400_BAD_REQUEST)

        session.status = 'accepted'
        session.save()

        # TODO: Send notification

        return Response({'status': 'accepted', 'message': 'Invitation accepted'})

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline invitation"""
        session = self.get_object()

        if session.invitee != request.user:
            return Response({'error': 'Only invitee can decline'}, status=status.HTTP_403_FORBIDDEN)

        session.status = 'declined'
        session.save()

        # Add optional message
        message_body = request.data.get('message')
        if message_body:
            Message.objects.create(session=session, sender=request.user, body=message_body)
            session.last_message_at = now()
            session.save()

        return Response({'status': 'declined', 'message': 'Invitation declined'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel session"""
        session = self.get_object()

        if request.user not in [session.inviter, session.invitee]:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        session.status = 'cancelled'
        session.save()

        # Add optional reason as message
        reason = request.data.get('reason')
        if reason:
            Message.objects.create(session=session, sender=request.user, body=f"Cancelled: {reason}")
            session.last_message_at = now()
            session.save()

        return Response({'status': 'cancelled', 'message': 'Session cancelled'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark session as completed"""
        session = self.get_object()

        if request.user not in [session.inviter, session.invitee]:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        session.status = 'completed'
        session.save()

        return Response({'status': 'completed', 'message': 'Session marked as completed. Please provide feedback.'})

    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        """Get or send messages"""
        session = self.get_object()

        if request.method == 'GET':
            messages = session.messages.all().order_by('created_at')
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            body = request.data.get('body')
            if not body:
                return Response({'error': 'Message body required'}, status=status.HTTP_400_BAD_REQUEST)

            message = Message.objects.create(
                session=session,
                sender=request.user,
                body=body
            )

            session.last_message_at = now()
            session.save()

            # TODO: Send notification

            return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark messages as read"""
        # TODO: Implement unread tracking (Phase 2 with separate read receipts table)
        return Response({'message': 'Messages marked as read'})
```

---

### 5.3 URLs

```python
# climbing_sessions/urls.py

from rest_framework.routers import DefaultRouter
from .views import SessionViewSet

router = DefaultRouter()
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = router.urls
```

**Generated URL patterns:**
- `POST /api/sessions/` - Create session (send invitation)
- `GET /api/sessions/` - List sessions
- `GET /api/sessions/{id}/` - Get session detail
- `POST /api/sessions/{id}/accept/` - Accept invitation
- `POST /api/sessions/{id}/decline/` - Decline invitation
- `POST /api/sessions/{id}/cancel/` - Cancel session
- `POST /api/sessions/{id}/complete/` - Mark as completed
- `GET /api/sessions/{id}/messages/` - Get messages
- `POST /api/sessions/{id}/messages/` - Send message
- `POST /api/sessions/{id}/mark-read/` - Mark messages as read

**Main URLs (config/urls.py):**
```python
urlpatterns = [
    # ... existing patterns
    path('api/', include('climbing_sessions.urls')),
]
```

---

## 6. Implementation Checklist

### Backend
- [ ] Create MessageSerializer (with UserSerializer import)
- [ ] Create SessionSerializer (with nested serializers)
- [ ] Create CreateSessionSerializer with:
  - [ ] TimeBlock.choices usage
  - [ ] Duplicate invitation check
  - [ ] Self-invite prevention
  - [ ] Trip date range validation
  - [ ] TODO comments for Phase 6 blocking
- [ ] Implement SessionViewSet with:
  - [ ] Rate limiting (10/h for create, 100/h for messages)
  - [ ] Proper queryset filtering (inviter/invitee)
  - [ ] Status and role filters
- [ ] Implement session actions:
  - [ ] accept (invitee only, pending status check)
  - [ ] decline (invitee only, optional message)
  - [ ] cancel (either party, optional reason)
  - [ ] complete (either party)
  - [ ] messages GET/POST
  - [ ] mark-read (placeholder for future)
- [ ] Create climbing_sessions/urls.py with router
- [ ] Add to config/urls.py
- [ ] Write unit tests

### Frontend
- [ ] Create session store
- [ ] Build session list page (`/sessions`)
- [ ] Build session detail/chat page (`/sessions/:id`)
- [ ] Build InviteModal component
- [ ] Build SessionCard component
- [ ] Build MessageList + MessageInput components
- [ ] Implement polling for messages
- [ ] Add notifications (browser notifications API)

### Testing
- [ ] Test full invitation flow (send → accept → chat → complete)
- [ ] Test decline/cancel flows
- [ ] Test blocked users cannot invite
- [ ] Test message sending/receiving
- [ ] Test polling

---

## 7. Estimated Timeline

- Backend session endpoints: 4 hours
- Backend message endpoints: 2 hours
- Frontend session list: 3 hours
- Frontend chat UI: 4 hours
- Invitation modal: 2 hours
- Testing: 2 hours
- **Total: ~17 hours**

---

## Recent Updates

**2026-01-13**: Updated spec to align with best practices and Phase 1-4 patterns:
- Fixed model field reference: `destination_name` → nested `destination` object with `trip.destination.name`
- Removed `Block.objects` validation (added TODO for Phase 6)
- Added duplicate invitation check in `CreateSessionSerializer`
- Added URL configuration section (5.3) with router setup
- Added missing imports: `Q`, `now()`, model/serializer imports
- Removed `unread_count` field (marked as future enhancement)
- Added rate limiting: 10 sessions/hour, 100 messages/hour
- Added error response documentation (400, 404)
- Updated `time_block` to use `TimeBlock.choices` (not hardcoded list)
- Added self-invite prevention validation
- Updated implementation checklist with detailed subtasks
- Clarified notification TODOs (Phase 6+)

---

## Next Phase
**Phase 6: Trust & Safety (Block/Report/Feedback)**
