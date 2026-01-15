# Send Buddy - Implementation Plan

## Overview

This directory contains detailed specification documents for implementing Send Buddy, a climbing partner matchmaking web application.

## Phase Structure

The MVP is divided into 6 sequential phases:

### **Phase 1: Data Models & Grade System** (11 hours)
- Complete database schema (User, DisciplineProfile, Trip, Session, etc.)
- **Location models (Destination + Crag) with hierarchical structure**
- Grade conversion system (YDS/French/V-Scale)
- Seed data for grades, experience tags, and **~30-50 climbing destinations**
- **Deliverable:** All models migrated, admin interface working, locations seeded

📄 [Phase 1 Spec](./phase-1-data-models.md)

---

### **Phase 2: Authentication & User Management** (14 hours)
- User registration with email verification
- Login/logout with JWT
- Profile management (view, edit, avatar upload)
- Password reset flow
- **Deliverable:** Users can register, login, and manage profiles

📄 [Phase 2 Spec](./phase-2-authentication.md)

---

### **Phase 3: Trip & Availability Management** (19 hours)
- Create/edit/delete trips **with destination & crag selection**
- **Destination autocomplete** (search from seeded database)
- **Crag multi-select** for granular location
- Add availability blocks within trips
- Calendar UI for availability
- **Interactive map view** showing destinations with active trips
- **Deliverable:** Users can create trips with specific destinations/crags, explore map of active trips

📄 [Phase 3 Spec](./phase-3-trips.md)

---

### **Phase 4: Matching Algorithm & Feed** (17 hours)
- **Core matchmaking algorithm** with weighted scoring:
  - **Location overlap (30pts) - crag-aware matching**
  - Date overlap (20pts)
  - Discipline overlap (20pts)
  - Grade compatibility (15pts)
  - Risk tolerance (10pts)
  - Availability overlap (5pts)
- **Improved matching:** Same crag = 30pts, same destination = 20pts
- Match feed UI with ranked results
- Match detail view
- Filter & search
- **Deliverable:** Users see ranked, precise matches for their trips

📄 [Phase 4 Spec](./phase-4-matching.md)

---

### **Phase 5: Sessions & Messaging** (17 hours)
- Session-based invitations (tied to specific date/time/location)
- Accept/decline/cancel flows
- Session chat (REST polling MVP, WebSockets in Phase 2)
- Session completion
- **Deliverable:** Users can invite matches and coordinate sessions

📄 [Phase 5 Spec](./phase-5-sessions.md)

---

### **Phase 6: Trust & Safety** (15 hours)
- Block/unblock users
- Report users (with admin moderation)
- Post-session feedback (private in MVP)
- Safety guidelines page
- Admin moderation interface
- **Deliverable:** Full safety features, MVP complete

📄 [Phase 6 Spec](./phase-6-safety.md)

---

## Total Estimated Time: ~93 hours

**Breakdown:**
- Phase 1: 11 hours (+3 for location models)
- Phase 2: 14 hours
- Phase 3: 19 hours (+6 for map + autocomplete)
- Phase 4: 17 hours
- Phase 5: 17 hours
- Phase 6: 15 hours

**Working full-time:** 2-3 weeks
**Working part-time:** 4-6 weeks

---

## Implementation Order

**IMPORTANT:** Phases must be completed in order due to dependencies:

```
Phase 1 (Models)
    ↓
Phase 2 (Auth) ─────┐
    ↓               │
Phase 3 (Trips) ────┤
    ↓               │
Phase 4 (Matching) ─┤
    ↓               │
Phase 5 (Sessions) ─┤
    ↓               │
Phase 6 (Safety) ◄──┘
```

---

## Quick Start Guide

### 1. Read the Product Spec
Review the main [Product + Technical Spec](../README.md) to understand:
- Target users
- Core value proposition
- Key features

### 2. Review Phase 1 Spec First
Start with [Phase 1: Data Models](./phase-1-data-models.md) as it's the foundation.

### 3. Implement One Phase at a Time
- Read the entire phase spec
- Complete all backend work first
- Then complete frontend work
- Test thoroughly before moving to next phase

### 4. Use the Checklists
Each phase spec includes an **Implementation Checklist** — use it to track progress.

---

## Spec Document Structure

Each phase spec contains:

1. **Overview** — What this phase accomplishes
2. **Dependencies** — What must be done first
3. **Backend API Endpoints** — Complete API specification with request/response examples
4. **Frontend Implementation** — Pages, components, state management
5. **Backend Implementation Details** — Serializers, views, business logic
6. **Implementation Checklist** — Step-by-step tasks
7. **Estimated Timeline** — Hours breakdown
8. **Next Phase** — What comes after

---

## Key Technical Decisions

### Backend
- **Framework:** Django 5.0 + Django REST Framework
- **Database:** PostgreSQL (relational for complex queries)
- **Auth:** JWT tokens via `djangorestframework-simplejwt`
- **Real-time (Phase 2):** Django Channels for WebSockets

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State Management:** Zustand
- **API Client:** Fetch with auth middleware

### Infrastructure
- **Development:** Docker Compose for Postgres
- **Hosting (Future):**
  - Frontend: Vercel
  - Backend: Railway/Fly.io
  - Database: Managed Postgres
  - Media: Cloudflare R2

---

## Design Principles (from Product Spec)

1. **Matchmaking > Directory** — Show best matches first, not a generic list
2. **Safety First** — Trust features built-in from day 1
3. **Travel-Aware** — Date/location overlap is core to matching
4. **Session-Based** — Conversations tied to specific climbing plans
5. **Simple UX** — Don't overcomplicate early

---

## Testing Strategy

### Unit Tests
- Backend: Models, serializers, matching algorithm
- Frontend: Utilities, API client

### Integration Tests
- Full user flows (register → create trip → find match → invite → session)
- Matching algorithm accuracy
- Block/report enforcement

### Manual Testing
- Cross-browser (Chrome, Safari, Firefox)
- Mobile responsive
- Email flows
- Edge cases (no matches, blocked users, expired tokens)

---

## Post-MVP Enhancements (Phase 2+)

After completing Phase 6, consider:

### High Priority
- WebSockets for real-time chat
- Push notifications (web + mobile)
- Destination autocomplete (Google Places or seed data)
- Public reputation scores

### Medium Priority
- Mobile app (React Native)
- Crag database with photos
- Calendar sync (iCal export)
- Better onboarding wizard

### Low Priority
- Social features (groups, forums)
- Trip recommendations
- Gear marketplace
- Event/competition listings

---

## Questions While Implementing?

Refer back to:
1. Original product spec (top-level README)
2. Relevant phase spec
3. Django/Next.js docs

**Default Rule:** When in doubt, choose the simplest option that preserves core matchmaking value.

---

## Phase Completion Criteria

### Phase 1 ✅
- [ ] All models created and migrated
- [ ] Grade conversion working for YDS/French/V-Scale
- [ ] Seed data loaded
- [ ] Admin interface functional

### Phase 2 ✅
- [ ] Registration with email verification working
- [ ] Login/logout working
- [ ] Profile CRUD complete
- [ ] Password reset flow working

### Phase 3 ✅
- [ ] Trip creation/edit/delete working
- [ ] Availability calendar UI complete
- [ ] Can add/edit/delete availability blocks

### Phase 4 ✅
- [ ] Matching algorithm returns ranked results
- [ ] Match feed UI shows top matches
- [ ] Filtering works
- [ ] Blocked users excluded from matches

### Phase 5 ✅
- [ ] Can send invitations
- [ ] Accept/decline flow works
- [ ] Chat working (polling)
- [ ] Session completion works

### Phase 6 ✅
- [ ] Block/unblock working
- [ ] Report flow working
- [ ] Feedback submission working
- [ ] Admin moderation functional
- [ ] **MVP COMPLETE** 🎉

---

## Contributors

Built with [Claude Code](https://claude.com/claude-code)

---

Ready to start building? Begin with **[Phase 1: Data Models & Grade System](./phase-1-data-models.md)**
