# Send Buddy

A climbing partner matchmaking web application that helps climbers (especially solo travelers) find compatible climbing partners based on skill level, location, dates, and safety preferences.

## Tech Stack

### Backend
- Django 5.0 + Django REST Framework
- PostgreSQL
- JWT Authentication
- psycopg3

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- React

## Project Structure

```
send_buddy/
├── backend/               # Django backend
│   ├── config/           # Django project settings
│   ├── users/            # User management app
│   ├── trips/            # Trip/availability management
│   ├── matching/         # Matching algorithm
│   ├── climbing_sessions/# Session & messaging
│   ├── manage.py
│   └── requirements.txt
├── frontend/             # Next.js frontend
│   ├── app/             # Next.js app directory
│   ├── components/      # React components
│   ├── lib/             # Utilities (API client, etc.)
│   └── package.json
└── docker-compose.yml   # PostgreSQL container
```

## Setup Instructions

### Prerequisites
- Python 3.14+ (or 3.11+)
- Node.js 18+
- PostgreSQL 15+ (or Docker)
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd send_buddy
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your database credentials
# For local Postgres:
POSTGRES_DB=send_buddy
POSTGRES_USER=<your-postgres-username>
POSTGRES_PASSWORD=<your-postgres-password>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Create database (if using local Postgres)
createdb send_buddy

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

Backend API will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file
cp .env.example .env.local

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:3000`

### 4. Using Docker for PostgreSQL (Alternative)

If you prefer to use Docker for PostgreSQL:

```bash
# Start PostgreSQL container
docker-compose up -d

# Update backend/.env to use port 5433
POSTGRES_PORT=5433

# Then run migrations as usual
cd backend
source venv/bin/activate
python manage.py migrate
```

## Development

### Running the Full Stack

1. Terminal 1: Start backend
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

2. Terminal 2: Start frontend
```bash
cd frontend
npm run dev
```

3. Visit `http://localhost:3000` to see the app

### API Endpoints

Currently available:
- `GET /api/health/` - Health check endpoint
- `POST /api/auth/token/` - Obtain JWT token
- `POST /api/auth/token/refresh/` - Refresh JWT token

## Next Steps

The initial project structure is set up. The next phase will involve:

1. **Data Models** - Implementing the full database schema (User profiles, Trips, Sessions, etc.)
2. **Grade Conversion System** - Building the climbing grade conversion logic
3. **Matching Algorithm** - Core matchmaking logic with weighted scoring
4. **Authentication** - User registration, login, profile management
5. **Trip Management** - Creating and managing climbing trips
6. **Matching Feed** - Displaying ranked matches
7. **Sessions & Chat** - Invitation system and messaging

## Configuration

### Backend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `send_buddy` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `postgres` |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `DJANGO_SECRET_KEY` | Django secret key | (auto-generated) |
| `DJANGO_DEBUG` | Debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | CORS origins | `http://localhost:3000` |

### Frontend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## License

MIT
