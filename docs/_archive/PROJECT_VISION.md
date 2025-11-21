# Glassdome - Agentic Cyber Range Deployment Framework

## Vision

Glassdome is an autonomous, intelligent deployment framework for cybersecurity cyber range lab environments. It combines AI-driven agents with multi-cloud orchestration to provide a seamless, drag-and-drop experience for deploying complex security testing environments.

## Problem Statement

Deploying cybersecurity lab environments is:
- Time-consuming and manual
- Complex across multiple platforms (Proxmox, Azure, AWS)
- Difficult to orchestrate multi-VM scenarios
- Hard to reproduce and share
- Requires deep technical knowledge

## Solution

An **agentic framework** that:
- Autonomously deploys lab elements based on high-level specifications
- Intelligently manages resources across Proxmox and cloud providers
- Provides a visual drag-and-drop interface for lab design
- Orchestrates complex multi-node environments
- Integrates with research systems for automated lab generation

## Core Components

### 1. Agentic Framework
- **Deployment Agents**: Autonomous agents for VM creation, configuration, and deployment
- **Orchestration Agents**: Manage complex multi-component scenarios
- **Monitoring Agents**: Track deployment status and health
- **Optimization Agents**: Resource allocation and cost optimization

### 2. Deployment Platforms

#### Proxmox (Primary)
- Direct API integration
- VM template management
- Network configuration
- Snapshot and clone operations
- Resource monitoring

#### Cloud Providers
- **Azure**: Resource groups, VMs, networks, security groups
- **AWS**: EC2, VPC, security groups, IAM
- Hybrid deployments across platforms

### 3. Frontend (React)
- **Drag-and-Drop Canvas**: Visual lab designer
- **Component Library**: Pre-built lab elements (VMs, networks, services)
- **Real-time Status**: Live deployment monitoring
- **Template Management**: Save and reuse lab configurations
- **Dashboard**: Overview of all deployments and resources

### 4. Orchestration Engine
- Dependency management between components
- Sequential and parallel deployment
- Rollback capabilities
- State management
- Configuration validation

### 5. Research Integration
- API endpoints to receive lab specifications from research system
- Automated translation of requirements to deployments
- Feedback loop for optimization

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Drag & Drop  │  │  Dashboard   │  │  Templates   │    │
│  │   Canvas     │  │   Monitor    │  │   Library    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ API Routes   │  │ Auth & RBAC  │  │ WebSocket    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Agentic Orchestration Layer                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Manager - Coordinates all autonomous agents   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Deployment  │  │ Monitoring   │  │ Optimization │    │
│  │   Agents     │  │   Agents     │  │   Agents     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Platform Integration Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Proxmox    │  │    Azure     │  │     AWS      │    │
│  │     API      │  │     API      │  │     API      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Data Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  PostgreSQL  │  │    Redis     │  │  TimeSeries  │    │
│  │ (Config/State│  │   (Queue)    │  │  (Metrics)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### Autonomous Deployment
- Agents make intelligent decisions about resource allocation
- Self-healing deployments
- Automatic retry and fallback mechanisms
- Learning from deployment patterns

### Visual Lab Design
- Drag nodes (VMs) onto canvas
- Connect with network links
- Configure properties via side panel
- Real-time validation
- Save as templates

### Multi-Platform Support
- Primary: Proxmox (on-premise)
- Cloud: Azure and AWS
- Hybrid deployments
- Platform-agnostic lab definitions

### Orchestration
- Complex dependency graphs
- Parallel execution where possible
- Progress tracking
- Rollback on failure
- State persistence

### Lab Elements
- **Attack VMs**: Kali, Parrot, custom
- **Vulnerable Targets**: DVWA, Metasploitable, custom
- **Network Devices**: Routers, firewalls, switches
- **Services**: Web servers, databases, domain controllers
- **Monitoring**: SIEM, IDS/IPS, logging

## Use Cases

1. **Training Labs**: Spin up isolated environments for security training
2. **Red Team Exercises**: Deploy attack/defense scenarios
3. **Vulnerability Testing**: Create test environments for security research
4. **CTF Events**: Rapid deployment of competition infrastructure
5. **Security Research**: Reproducible lab environments
6. **Certification Prep**: OSCP, CEH, CISSP lab environments

## Technical Specifications

### Backend Stack
- **Python 3.11+**: Core language
- **FastAPI**: API framework
- **SQLAlchemy**: ORM for database
- **Celery**: Task queue for long-running deployments
- **Redis**: Message broker and caching
- **PostgreSQL**: Primary database

### Frontend Stack
- **React 18**: UI framework
- **React Flow**: Drag-and-drop canvas
- **Redux/Zustand**: State management
- **TailwindCSS**: Styling
- **Socket.io**: Real-time updates

### Infrastructure
- **Docker**: Containerization
- **Proxmox**: Primary hypervisor
- **Azure/AWS**: Cloud providers
- **Terraform**: Infrastructure as Code (optional)

## Development Phases

### Phase 1: Foundation (Current)
- [x] Project structure
- [ ] Core agent framework
- [ ] Basic Proxmox integration
- [ ] Database models
- [ ] Basic API endpoints

### Phase 2: Core Features
- [ ] Full Proxmox API integration
- [ ] Agent orchestration system
- [ ] Basic React canvas
- [ ] VM deployment capabilities
- [ ] State management

### Phase 3: Cloud Integration
- [ ] Azure API integration
- [ ] AWS API integration
- [ ] Multi-cloud orchestration
- [ ] Resource cost tracking

### Phase 4: Advanced Features
- [ ] Template library
- [ ] Automated network configuration
- [ ] Advanced monitoring
- [ ] Research system integration
- [ ] AI-powered optimization

### Phase 5: Production
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Documentation
- [ ] Testing suite
- [ ] Deployment automation

## Security Considerations

- API key management for cloud providers
- RBAC for user permissions
- Encrypted secrets storage
- Audit logging
- Network isolation for deployed labs
- Secure VM templates

## Success Metrics

- Time to deploy a lab environment (< 5 minutes)
- Success rate of autonomous deployments (> 95%)
- User satisfaction with drag-and-drop interface
- Cost optimization vs manual deployment
- Number of reusable templates created

## Future Enhancements

- AI-powered lab generation from descriptions
- Integration with vulnerability databases
- Automated attack scenario generation
- ML-based resource optimization
- Marketplace for lab templates
- Community template sharing

---

**Glassdome: Making Cyber Range Deployment Autonomous and Accessible**

