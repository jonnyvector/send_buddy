# Matching API - Quick Reference Guide

## Base URL
```
http://localhost:8000/api
```

## Authentication
All endpoints require JWT authentication:
```
Authorization: Bearer <access_token>
```

---

## Endpoints

### 1. List Matches

**GET** `/api/matches/`

Get matches for authenticated user's next upcoming trip (or specified trip).

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `trip` | UUID | No | Next upcoming trip | Specific trip ID to match for |
| `limit` | Integer | No | 10 | Maximum matches to return (max: 50) |

#### Success Response (200 OK):
```json
{
  "trip": {
    "id": "uuid",
    "destination": {
      "slug": "string",
      "name": "string",
      "country": "string",
      "lat": "decimal",
      "lng": "decimal",
      "primary_disciplines": ["string"],
      "season": "string"
    },
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "preferred_disciplines": ["string"]
  },
  "matches": [
    {
      "user": {
        "id": "uuid",
        "display_name": "string",
        "avatar": "url or null",
        "bio": "string",
        "home_location": "string",
        "risk_tolerance": "conservative | balanced | aggressive",
        "disciplines": [
          {
            "id": "uuid",
            "discipline": "sport | trad | bouldering | multipitch | gym",
            "grade_system": "yds | french | v_scale",
            "comfortable_grade_min_display": "string",
            "comfortable_grade_max_display": "string",
            "can_lead": boolean,
            "can_belay": boolean,
            "can_build_anchors": boolean
          }
        ],
        "experience_tags": ["string"]
      },
      "trip": {
        "id": "uuid",
        "destination": {...},
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "preferred_disciplines": ["string"]
      },
      "match_score": 0-100,
      "reasons": ["string"],
      "overlap_dates": {
        "start": "YYYY-MM-DD",
        "end": "YYYY-MM-DD",
        "days": integer
      }
    }
  ]
}
```

#### Error Responses:
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - No upcoming trips or invalid trip ID

#### Example Requests:

**Get matches for next trip:**
```bash
curl -X GET "http://localhost:8000/api/matches/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Get matches for specific trip:**
```bash
curl -X GET "http://localhost:8000/api/matches/?trip=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Get top 5 matches:**
```bash
curl -X GET "http://localhost:8000/api/matches/?limit=5" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 2. Match Detail

**GET** `/api/matches/<user_id>/detail/`

Get detailed match information for a specific user.

#### Path Parameters:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | Yes | ID of the matched user |

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `trip` | UUID | No | Next upcoming trip | Specific trip ID to match for |

#### Success Response (200 OK):
```json
{
  "user": {
    "id": "uuid",
    "display_name": "string",
    "avatar": "url or null",
    "bio": "string",
    "home_location": "string",
    "risk_tolerance": "conservative | balanced | aggressive",
    "disciplines": [...],
    "experience_tags": ["string"]
  },
  "trip": {
    "id": "uuid",
    "destination": {...},
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "preferred_disciplines": ["string"]
  },
  "match_score": 0-100,
  "reasons": ["string"],
  "overlap_dates": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD",
    "days": integer
  }
}
```

#### Error Responses:
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Match not found or no upcoming trips

#### Example Request:
```bash
curl -X GET "http://localhost:8000/api/matches/987fcdeb-51a2-43d7-8f9a-123456789abc/detail/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Match Scoring System

Matches are scored on a 100-point scale:

| Factor | Max Points | Description |
|--------|------------|-------------|
| **Location** | 30 | Same destination + crag overlap |
| **Date Overlap** | 20 | Number of overlapping days (4 pts/day) |
| **Discipline** | 20 | Shared climbing disciplines |
| **Grade Compatibility** | 15 | Overlapping grade ranges |
| **Risk Tolerance** | 10 | Matching risk preferences |
| **Availability** | 5 | Matching time blocks |
| **Total** | **100** | Minimum threshold: 20 points |

### Location Scoring Breakdown:
- 30 points: Same destination + overlapping crags
- 25 points: Same destination + no crag preference (flexible)
- 20 points: Same destination + different crags
- 0 points: Different destinations

### Risk Tolerance Scoring:
- 10 points: Same tolerance
- 3 points: One level difference
- -10 points: Two level difference

---

## Common Use Cases

### 1. Display Matches for Current Trip
```javascript
async function getMatches() {
  const response = await fetch('/api/matches/', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  if (!response.ok) {
    if (response.status === 404) {
      console.log('No upcoming trips');
    }
    return;
  }

  const data = await response.json();
  return data.matches;
}
```

### 2. Get Top 3 Matches
```javascript
async function getTopMatches() {
  const response = await fetch('/api/matches/?limit=3', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  const data = await response.json();
  return data.matches;
}
```

### 3. View Match Details
```javascript
async function getMatchDetail(userId) {
  const response = await fetch(`/api/matches/${userId}/detail/`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  const data = await response.json();
  return data;
}
```

### 4. Display Match Cards
```javascript
function renderMatchCard(match) {
  return `
    <div class="match-card">
      <img src="${match.user.avatar || '/default-avatar.jpg'}" />
      <h3>${match.user.display_name}</h3>
      <p>${match.user.bio}</p>
      <div class="match-score">
        <span>${match.match_score}</span>
        <span>Match Score</span>
      </div>
      <div class="match-details">
        <p>📍 ${match.user.home_location}</p>
        <p>📅 ${match.overlap_dates.days} days overlap</p>
        <p>🧗 ${match.user.disciplines.map(d => d.discipline).join(', ')}</p>
      </div>
      <div class="match-reasons">
        ${match.reasons.map(r => `<span class="badge">${r}</span>`).join('')}
      </div>
    </div>
  `;
}
```

---

## Privacy & Security Notes

### Automatic Filtering:
- ✅ Blocked users are automatically excluded (both directions)
- ✅ Only verified, visible profiles are shown
- ✅ Only active trips are considered
- ✅ Users can only access their own trip data

### Best Practices:
1. Always handle 404 responses (user may have no trips)
2. Respect the limit parameter (don't request >50 matches)
3. Cache match results on frontend for better UX
4. Show loading states while fetching matches

---

## Testing Endpoints

### Using cURL:

**1. Get JWT Token:**
```bash
curl -X POST "http://localhost:8000/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

**2. Use Token to Get Matches:**
```bash
curl -X GET "http://localhost:8000/api/matches/" \
  -H "Authorization: Bearer <access_token_from_step_1>"
```

### Using Python:
```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login/', json={
    'email': 'user@example.com',
    'password': 'password123'
})
token = response.json()['access']

# Get matches
matches_response = requests.get(
    'http://localhost:8000/api/matches/',
    headers={'Authorization': f'Bearer {token}'}
)
matches = matches_response.json()

print(f"Found {len(matches['matches'])} matches")
for match in matches['matches']:
    print(f"{match['user']['display_name']}: {match['match_score']} points")
```

---

## Rate Limiting

- **Rate**: 30 requests per minute per user
- **Scope**: Per authenticated user
- **HTTP Header**: `X-RateLimit-Remaining`

If rate limited, you'll receive:
```json
{
  "detail": "Request was throttled. Expected available in X seconds."
}
```

---

## Support & Troubleshooting

### Common Issues:

**1. "No upcoming trips" error**
- User must have at least one trip with `start_date >= today`
- Trip must be marked as `is_active=true`

**2. Empty matches array**
- No other users have overlapping trips to same destination
- All potential matches are below 20-point threshold
- User may have blocked all potential matches

**3. 401 Unauthorized**
- Access token expired (15 minutes lifetime)
- Use refresh token to get new access token

### Contact:
For bugs or feature requests, please file an issue in the repository.
