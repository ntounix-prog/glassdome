# Glassdome Setup Guide

Complete setup guide for the Glassdome project.

## Prerequisites

- **Python 3.11+** - Backend runtime
- **Node.js 20+** - Frontend runtime  
- **Docker & Docker Compose** (optional) - For containerized deployment
- **Git** - Version control

## Installation Methods

### 1. Docker Setup (Recommended for Production)

Docker provides the most consistent environment across different systems.

```bash
# Clone the repository
git clone <your-repo-url>
cd glassdome

# Start with Docker Compose
docker-compose up --build
```

**Access the application:**
- Frontend: http://localhost:5173 (dev) or http://localhost:8000 (production)
- Backend API: http://localhost:8000/api
- API Docs: http://localhost:8000/docs

### 2. Local Development Setup

For active development with hot reload and better debugging.

#### Step 1: Backend Setup

```bash
# Run the automated setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 2: Frontend Setup

```bash
cd frontend
npm install
```

#### Step 3: Run Development Servers

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 3. Quick Start with Make

```bash
make setup        # Initial setup
make install      # Update dependencies
make clean        # Clean environment
```

## Configuration

### Environment Variables

1. Copy the example environment file:
```bash
cp env.example .env
```

2. Edit `.env` with your configuration:
```env
ENVIRONMENT=development
BACKEND_PORT=8000

# Add your API keys
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

### Backend Configuration

Edit `backend/main.py` to:
- Configure CORS origins
- Add new API routes
- Set up database connections
- Configure middleware

### Frontend Configuration

Edit `frontend/vite.config.js` to:
- Change ports
- Configure proxy settings
- Add build optimizations

## Verification

### Check Backend

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "message": "Glassdome API is running"
}
```

### Check Frontend

Open http://localhost:5173 in your browser. You should see the Glassdome landing page with a backend health check.

## Common Issues

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Python Virtual Environment Issues

```bash
# Remove and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node Module Issues

```bash
# Clean install
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Docker Issues

```bash
# Clean rebuild
docker-compose down -v
docker-compose up --build
```

## Next Steps

- Read the [Architecture Documentation](./ARCHITECTURE.md)
- Check out the [API Documentation](http://localhost:8000/docs) when running
- Review the [Contributing Guidelines](./CONTRIBUTING.md)

