# Glassdome Authors & Contributors

## Original Author

**Brett Turner** (ntounix-prog)  
*Founder & Lead Developer*  
*November 2025 - Present*

All original code, architecture, and design created by Brett Turner with AI-assisted development.

---

## Core Architecture (v0.1.0 - v0.6.0)

The following components were designed and implemented by the original author:

### Backend (Python/FastAPI)
- `glassdome/api/` - All API endpoints (reaper, whiteknight, canvas_deploy, registry, platforms)
- `glassdome/platforms/` - Platform clients (Proxmox, ESXi, AWS, Azure)
- `glassdome/registry/` - Lab Registry with Redis backend, agents, controllers
- `glassdome/reaper/` - Reaper exploit library and hot spare pool
- `glassdome/workers/` - Celery task workers
- `glassdome/chat/` - Overseer AI agent
- `glassdome/core/` - Configuration, database, SSH utilities
- `glassdome/networking/` - Network orchestration
- `glassdome/whitepawn/` - WhitePawn orchestrator
- `glassdome/overseer/` - Overseer entity management

### Frontend (React/Vite)
- `frontend/src/pages/` - All page components (Dashboard, LabCanvas, ReaperDesign, etc.)
- `frontend/src/components/` - Reusable components (OverseerChat, NetworkMap, etc.)
- `frontend/src/hooks/` - Custom React hooks
- `frontend/src/styles/` - All CSS styling

### Infrastructure
- Proxmox cluster architecture (2-node HA)
- TrueNAS NFS shared storage integration
- Nexus 3064X SAN switch configuration
- pfSense-as-gateway lab network design
- Guacamole (Updock) player access system

### Documentation
- All session logs and technical documentation
- AGENT_CONTEXT.md for AI assistant onboarding
- Architecture diagrams and code inventory

---

## Version History

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | Nov 2025 | Initial architecture, Proxmox integration |
| 0.2.0 | Nov 2025 | Reaper missions, WhiteKnight validation |
| 0.3.0 | Nov 2025 | Canvas lab deployment |
| 0.4.0 | Nov 2025 | Lab Registry, real-time monitoring |
| 0.5.0 | Nov 2025 | Overseer chat, SomaFM integration |
| 0.6.0 | Nov 2025 | Player Portal, Guacamole integration |

---

## AI-Assisted Development

This project was developed with AI assistance (Claude/Cursor). The AI helped with:
- Code generation and refactoring
- Documentation writing
- Debugging and troubleshooting
- Architecture suggestions

All code was reviewed, tested, and approved by the original author.

---

## Future Contributors

*This section will be updated as the team grows.*

### How to Add Yourself
When contributing, add your name below with your contribution area:

```markdown
**Your Name** (@github-handle)
- Contribution area/feature
- Date joined
```

---

## License

Copyright (c) 2025 Brett Turner. All rights reserved.

*License terms to be determined before public release.*

