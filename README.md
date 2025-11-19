# Glassdome

A clean, well-structured project repository.

## Project Structure

```
glassdome/
├── backend/              # Python FastAPI backend
│   ├── main.py          # Main application entry
│   └── __init__.py      # Package initialization
├── frontend/            # React frontend (Vite)
│   ├── src/            # React source code
│   ├── package.json    # Node dependencies
│   └── vite.config.js  # Vite configuration
├── docs/               # Documentation files
├── agent_context/      # Agent context and configurations
├── venv/               # Virtual environment (created by setup)
├── Dockerfile          # Docker container definition
├── docker-compose.yml  # Docker orchestration
├── requirements.txt    # Python dependencies
├── package.json        # Root npm scripts
├── setup.sh           # Environment setup script
└── README.md          # This file
```

## Tech Stack

- **Backend**: Python + FastAPI + Uvicorn
- **Frontend**: React 18 + Vite
- **Containerization**: Docker + Docker Compose
- **Package Management**: pip (Python) + npm (Node.js)

## Getting Started

### Option 1: Docker (Recommended)

The easiest way to run the entire stack:

```bash
# Build and start all services
docker-compose up --build

# Or run in development mode with hot reload
docker-compose --profile dev up
```

- Backend API: http://localhost:8000
- Frontend Dev Server: http://localhost:5173
- API Documentation: http://localhost:8000/docs

### Option 2: Local Development

#### Backend Setup

```bash
# Create virtual environment and install dependencies
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Run the backend server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
# Install frontend dependencies
cd frontend
npm install

# Run the dev server
npm run dev
```

### Option 3: Using Make Commands

```bash
make setup    # Initial setup
make install  # Install/update dependencies
make clean    # Clean up environment
make help     # See all commands
```

## Development

### Adding Python Dependencies

Edit `requirements.txt` and run:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Adding Node Dependencies

```bash
cd frontend
npm install <package-name>
```

### Environment Variables

Copy `env.example` to `.env` and configure your environment variables.

## Documentation

Project documentation can be found in the `docs/` directory.

## License

(Add license information here)

