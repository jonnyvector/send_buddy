# WebSocket Integration Guide

## Overview

Send Buddy uses Django Channels to provide real-time messaging for climbing session chat. This document describes how to integrate WebSocket connections in the frontend.

## Prerequisites

### Backend Requirements
- Redis server running on `localhost:6379` (development) or configured via `REDIS_URL` environment variable (production)
- Django Channels installed and configured (see `requirements.txt`)
- ASGI server (Daphne) running

### Starting the Development Server

```bash
# Ensure Redis is running
redis-server

# Start the ASGI server (in backend directory)
source venv/bin/activate
python manage.py runserver
# OR use Daphne directly:
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

## WebSocket Connection

### Endpoint

```
ws://localhost:8000/ws/sessions/<session_id>/
```

- `session_id`: UUID of the climbing session

### Authentication

WebSocket connections require JWT authentication via query parameter:

```javascript
const token = "your_access_token_here";
const sessionId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(
  `ws://localhost:8000/ws/sessions/${sessionId}/?token=${token}`
);
```

### Connection Lifecycle

#### 1. Connection Established
```javascript
ws.onopen = (event) => {
  console.log("WebSocket connected");
};
```

#### 2. Connection Failed
The server will close the connection with specific error codes:

- `4001`: No token provided
- `4002`: User not found
- `4003`: Invalid or expired token
- `4004`: User is not a participant in this session

```javascript
ws.onclose = (event) => {
  console.log("WebSocket closed:", event.code, event.reason);

  if (event.code === 4003) {
    // Token expired, refresh and reconnect
  }
};
```

#### 3. Connection Errors
```javascript
ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};
```

## Message Format

### Sending Messages (Client → Server)

#### Chat Message
```javascript
ws.send(JSON.stringify({
  type: "message",
  content: "Hello, climbing partner!"
}));
```

**Validation:**
- `content` must be non-empty and ≤ 2000 characters
- Message is automatically persisted to database
- Session's `last_message_at` timestamp is updated

#### Typing Indicator
```javascript
// User starts typing
ws.send(JSON.stringify({
  type: "typing",
  is_typing: true
}));

// User stops typing
ws.send(JSON.stringify({
  type: "typing",
  is_typing: false
}));
```

### Receiving Messages (Server → Client)

#### Chat Message
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "message") {
    console.log({
      messageId: data.message_id,      // UUID
      content: data.content,            // String
      senderId: data.sender_id,         // UUID
      senderName: data.sender_name,     // String
      createdAt: data.created_at        // ISO 8601 timestamp
    });
  }
};
```

**Example Response:**
```json
{
  "type": "message",
  "message_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "content": "Hello, climbing partner!",
  "sender_id": "550e8400-e29b-41d4-a716-446655440000",
  "sender_name": "John Doe",
  "created_at": "2026-01-13T18:30:00.123456Z"
}
```

#### Typing Indicator
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "typing") {
    console.log({
      senderId: data.sender_id,         // UUID
      senderName: data.sender_name,     // String
      isTyping: data.is_typing          // Boolean
    });

    // Note: You won't receive your own typing indicators
  }
};
```

**Example Response:**
```json
{
  "type": "typing",
  "sender_id": "660e8400-e29b-41d4-a716-446655440000",
  "sender_name": "Jane Smith",
  "is_typing": true
}
```

## React Integration Example

```javascript
import { useState, useEffect, useRef } from 'react';

function SessionChat({ sessionId, accessToken }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const wsRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket(
      `ws://localhost:8000/ws/sessions/${sessionId}/?token=${accessToken}`
    );

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'message') {
        setMessages((prev) => [...prev, {
          id: data.message_id,
          content: data.content,
          senderId: data.sender_id,
          senderName: data.sender_name,
          createdAt: new Date(data.created_at),
        }]);
      } else if (data.type === 'typing') {
        setIsTyping(data.is_typing);

        // Auto-hide typing indicator after 3 seconds
        if (data.is_typing) {
          setTimeout(() => setIsTyping(false), 3000);
        }
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code);

      if (event.code === 4003) {
        // Handle token expiration - refresh token and reconnect
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [sessionId, accessToken]);

  const sendMessage = () => {
    if (!inputValue.trim() || !wsRef.current) return;

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content: inputValue.trim(),
    }));

    setInputValue('');
  };

  const handleTyping = () => {
    if (!wsRef.current) return;

    // Send typing indicator
    wsRef.current.send(JSON.stringify({
      type: 'typing',
      is_typing: true,
    }));

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Stop typing after 2 seconds of inactivity
    typingTimeoutRef.current = setTimeout(() => {
      wsRef.current.send(JSON.stringify({
        type: 'typing',
        is_typing: false,
      }));
    }, 2000);
  };

  return (
    <div>
      <div className="messages">
        {messages.map((msg) => (
          <div key={msg.id}>
            <strong>{msg.senderName}:</strong> {msg.content}
            <small>{msg.createdAt.toLocaleString()}</small>
          </div>
        ))}
        {isTyping && <div className="typing">Partner is typing...</div>}
      </div>

      <div className="input">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value);
            handleTyping();
          }}
          onKeyPress={(e) => {
            if (e.key === 'Enter') sendMessage();
          }}
          maxLength={2000}
          placeholder="Type a message..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default SessionChat;
```

## Security Considerations

1. **Authentication**: All WebSocket connections require a valid JWT access token
2. **Authorization**: Users can only connect to sessions where they are participants (inviter or invitee)
3. **Message Validation**: Content is validated for length (≤ 2000 characters)
4. **Token Expiration**: Handle 4003 error code by refreshing the token and reconnecting

## Token Refresh Strategy

When the access token expires (default: 15 minutes), implement a refresh strategy:

```javascript
async function connectWithTokenRefresh(sessionId) {
  let accessToken = localStorage.getItem('accessToken');

  const ws = new WebSocket(
    `ws://localhost:8000/ws/sessions/${sessionId}/?token=${accessToken}`
  );

  ws.onclose = async (event) => {
    if (event.code === 4003) {
      // Token expired - refresh it
      try {
        const response = await fetch('http://localhost:8000/api/auth/refresh/', {
          method: 'POST',
          credentials: 'include', // Include refresh token cookie
        });

        const data = await response.json();
        localStorage.setItem('accessToken', data.access);

        // Reconnect with new token
        connectWithTokenRefresh(sessionId);
      } catch (error) {
        console.error('Token refresh failed:', error);
        // Redirect to login
      }
    }
  };

  return ws;
}
```

## Production Deployment

### Redis Configuration

Set `REDIS_URL` environment variable in production:

```bash
# .env (production)
REDIS_URL=redis://your-redis-host:6379/0
# Or for Redis with password:
REDIS_URL=redis://:password@your-redis-host:6379/0
# Or for Redis Sentinel/Cluster:
REDIS_URL=redis://primary:6379,replica1:6379,replica2:6379/0
```

### ASGI Server

Use Daphne with a process manager (systemd, supervisor, or Docker):

```bash
# Run with Daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Or with Gunicorn + Uvicorn workers
gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### WebSocket URL

Update WebSocket URL for production:

```javascript
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsHost = window.location.host; // e.g., 'api.sendbuddy.com'
const ws = new WebSocket(
  `${wsProtocol}//${wsHost}/ws/sessions/${sessionId}/?token=${token}`
);
```

## Testing

### Manual Testing with wscat

Install wscat:
```bash
npm install -g wscat
```

Connect and test:
```bash
# Connect to WebSocket
wscat -c "ws://localhost:8000/ws/sessions/YOUR_SESSION_ID/?token=YOUR_ACCESS_TOKEN"

# Send a message
> {"type": "message", "content": "Test message"}

# Send typing indicator
> {"type": "typing", "is_typing": true}
```

### Automated Testing

See `climbing_sessions/tests/test_consumers.py` for consumer unit tests.

## Troubleshooting

### Connection Refused
- Ensure Redis is running: `redis-cli ping` should return `PONG`
- Ensure ASGI server is running on port 8000
- Check firewall settings

### Authentication Errors (4003)
- Verify token is valid and not expired
- Check token format in query parameter
- Ensure JWT secret keys match between environments

### Messages Not Broadcasting
- Check Redis connection in Django shell:
  ```python
  from channels.layers import get_channel_layer
  channel_layer = get_channel_layer()
  # Should not raise errors
  ```
- Verify session_id is valid UUID format
- Ensure both users are participants in the session

### Database Not Saving Messages
- Check Message model migrations are applied
- Verify database connection settings
- Check Django logs for errors

## Support

For issues or questions:
1. Check Django logs: `python manage.py runserver` output
2. Check Redis logs: `redis-cli monitor`
3. Use browser DevTools Network tab to inspect WebSocket frames
4. Review `climbing_sessions/consumers.py` for server-side logic
