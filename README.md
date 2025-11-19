# Glassdome 🔮

**Agentic Cyber Range Deployment Framework**

Glassdome is an autonomous, AI-powered deployment system for cybersecurity lab environments. Using intelligent agents and a visual drag-and-drop interface, deploy complex cyber range scenarios to Proxmox, Azure, or AWS in minutes.

## 🎯 Key Features

- **🤖 Autonomous Agents** - AI-powered agents handle complex deployments automatically
- **🎨 Drag & Drop Designer** - Visual canvas for designing cyber range labs
- **☁️ Multi-Platform** - Deploy to Proxmox, Azure, or AWS seamlessly
- **🔄 Smart Orchestration** - Dependency management and parallel execution
- **📊 Real-time Monitoring** - Track deployment progress and resource health
- **📚 Template Library** - Reusable lab configurations for common scenarios

## 🏗️ Project Structure

```
glassdome/
├── backend/                      # Python FastAPI backend
│   ├── agents/                  # Autonomous agent framework
│   │   ├── base.py             # Base agent classes
│   │   └── manager.py          # Agent coordination
│   ├── orchestration/           # Deployment orchestration
│   │   └── engine.py           # Orchestration engine
│   ├── platforms/               # Platform integrations
│   │   ├── proxmox_client.py   # Proxmox API
│   │   ├── azure_client.py     # Azure API  
│   │   └── aws_client.py       # AWS API
│   ├── models/                  # Database models
│   │   ├── lab.py              # Lab configurations
│   │   ├── deployment.py       # Deployment tracking
│   │   └── platform.py         # Platform configs
│   ├── core/                    # Core configuration
│   │   ├── config.py           # Settings
│   │   └── database.py         # Database setup
│   └── main.py                 # API entry point
├── frontend/                    # React frontend (Vite)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx   # Main dashboard
│   │   │   ├── LabCanvas.jsx   # Drag-and-drop lab designer
│   │   │   └── Deployments.jsx # Deployment monitoring
│   │   └── styles/             # Component styles
│   ├── package.json            # Node dependencies
│   └── vite.config.js          # Vite configuration
├── docs/                        # Comprehensive documentation
│   ├── PROJECT_VISION.md       # Project vision and goals
│   ├── ARCHITECTURE.md         # System architecture
│   ├── SETUP.md                # Setup instructions
│   ├── API.md                  # API documentation
│   └── GIT_SETUP.md            # Git workflow
├── agent_context/              # Agent context files
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Multi-stage build
└── requirements.txt            # Python dependencies
```

## 🛠️ Tech Stack

### Backend
- **Python 3.11+** - Core language
- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - ORM for database operations
- **Celery + Redis** - Task queue for long-running operations
- **LangChain** - AI agent framework

### Frontend
- **React 18** - UI framework
- **Vite** - Lightning-fast build tool
- **React Flow** - Drag-and-drop canvas
- **Zustand** - State management

### Platform Integrations
- **Proxmoxer** - Proxmox VE API client
- **Boto3** - AWS SDK
- **Azure SDK** - Azure management clients

### Infrastructure
- **PostgreSQL** - Primary database
- **Redis** - Caching and message broker
- **Docker** - Containerization

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

