# Glassdome Quick Start 🚀

Get up and running in 5 minutes!

## Prerequisites Check

```bash
python3 --version  # Should be 3.11+
node --version     # Should be 20+
docker --version   # Optional but recommended
```

## Method 1: Docker (Fastest) 🐳

```bash
# 1. Start everything
docker-compose up --build

# 2. Open your browser
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/api
# API Docs: http://localhost:8000/docs

# That's it! ✨
```

## Method 2: Local Development 💻

### Backend (Terminal 1)

```bash
# Setup Python environment
./setup.sh

# Activate and run
source venv/bin/activate
cd backend
python main.py
```

### Frontend (Terminal 2)

```bash
# Install and run
cd frontend
npm install
npm run dev
```

### Access

- Frontend: http://localhost:5173
- Backend: http://localhost:8000/api
- API Docs: http://localhost:8000/docs

## Verify Installation ✅

```bash
# Test backend
curl http://localhost:8000/api/health

# Expected: {"status": "healthy", "message": "Glassdome API is running"}
```

## What's Next?

1. **Read the docs**: Check out `docs/` folder
2. **Explore the code**: 
   - Backend: `backend/main.py`
   - Frontend: `frontend/src/App.jsx`
3. **Add features**: Start building!

## Common Commands

```bash
# Backend
source venv/bin/activate        # Activate Python env
pip install <package>           # Add Python package
uvicorn backend.main:app --reload  # Run with hot reload

# Frontend
npm install <package>           # Add Node package
npm run dev                     # Development server
npm run build                   # Production build

# Docker
docker-compose up               # Start
docker-compose down             # Stop
docker-compose logs -f          # View logs
```

## Troubleshooting

**Port 8000 in use?**
```bash
lsof -i :8000
kill -9 <PID>
```

**Module not found?**
```bash
# Backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

## Need Help?

- Full setup guide: `docs/SETUP.md`
- Architecture: `docs/ARCHITECTURE.md`
- Main README: `README.md`

