#!/usr/bin/env python3
"""
Send Glassdome Welcome Email

Sends a welcome email to new team members with build history and feature overview.

Author: Brett Turner (ntounix)
Created: December 2025
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()

from glassdome.integrations.mailcow_client import MailcowClient


def get_welcome_email_html():
    """Generate HTML welcome email with Glassdome overview."""
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #00d4ff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 42px;
            margin-bottom: 10px;
        }}
        h1 {{
            color: #0a0e1a;
            margin: 0;
        }}
        h1 span.glass {{ color: #00d4ff; }}
        h1 span.dome {{ color: #333; }}
        .tagline {{
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-top: 5px;
        }}
        h2 {{
            color: #00d4ff;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        h3 {{
            color: #333;
            margin-top: 20px;
        }}
        .feature-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .feature-card {{
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #00d4ff;
        }}
        .feature-card.active {{
            border-left-color: #00ff64;
            background: linear-gradient(135deg, #f0fff4, #e6ffe6);
        }}
        .feature-icon {{
            font-size: 24px;
            margin-bottom: 5px;
        }}
        .feature-title {{
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }}
        .feature-desc {{
            font-size: 13px;
            color: #666;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-active {{
            background: #00ff64;
            color: #0a0e1a;
        }}
        .badge-version {{
            background: #00d4ff;
            color: white;
        }}
        .timeline {{
            border-left: 3px solid #00d4ff;
            padding-left: 20px;
            margin: 20px 0;
        }}
        .timeline-item {{
            position: relative;
            padding-bottom: 20px;
        }}
        .timeline-item::before {{
            content: '';
            position: absolute;
            left: -26px;
            top: 5px;
            width: 12px;
            height: 12px;
            background: #00d4ff;
            border-radius: 50%;
        }}
        .timeline-date {{
            font-size: 12px;
            color: #888;
            font-weight: 600;
        }}
        .timeline-title {{
            font-weight: 600;
            color: #333;
        }}
        .timeline-desc {{
            font-size: 14px;
            color: #666;
        }}
        .code-block {{
            background: #0a0e1a;
            color: #00d4ff;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 13px;
            overflow-x: auto;
        }}
        .stats-row {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
            padding: 20px;
            background: linear-gradient(135deg, #0a0e1a, #1a1e2a);
            border-radius: 8px;
            color: white;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: #00d4ff;
        }}
        .stat-label {{
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #888;
            font-size: 12px;
        }}
        a {{
            color: #00d4ff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🔮</div>
            <h1><span class="glass">GLASS</span><span class="dome">DOME</span></h1>
            <div class="tagline">Autonomous Cyber Range Operations</div>
            <span class="badge badge-version">v0.7.0</span>
        </div>

        <p>Welcome to <strong>Glassdome</strong> – an AI-powered agentic framework for deploying cybersecurity training lab environments in minutes, not hours.</p>

        <h2>🎯 What Is Glassdome?</h2>
        <p>Glassdome is an <strong>Agentic Cyber Range Deployment Framework</strong> that autonomously deploys complex cybersecurity lab environments across multiple virtualization platforms. It combines intelligent agents with infrastructure-as-code to create a seamless deployment experience.</p>

        <div class="stats-row">
            <div class="stat">
                <div class="stat-value">4</div>
                <div class="stat-label">Platforms</div>
            </div>
            <div class="stat">
                <div class="stat-value">15</div>
                <div class="stat-label">Features</div>
            </div>
            <div class="stat">
                <div class="stat-value">47s</div>
                <div class="stat-label">Avg Deploy</div>
            </div>
            <div class="stat">
                <div class="stat-value">78</div>
                <div class="stat-label">Tests Pass</div>
            </div>
        </div>

        <h2>✨ Core Features</h2>
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <div class="feature-title">Autonomous Agents</div>
                <div class="feature-desc">AI-powered deployment agents handle complex orchestration automatically</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🎨</div>
                <div class="feature-title">Visual Lab Designer</div>
                <div class="feature-desc">Drag-and-drop canvas with ReactFlow for intuitive lab creation</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">☁️</div>
                <div class="feature-title">Multi-Platform</div>
                <div class="feature-desc">Deploy to Proxmox, Azure, AWS, or hybrid environments</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <div class="feature-title">Rapid Deployment</div>
                <div class="feature-desc">Go from design to deployed lab in minutes, not hours</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔄</div>
                <div class="feature-title">Orchestration</div>
                <div class="feature-desc">Complex dependency management and parallel execution</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Real-time Monitoring</div>
                <div class="feature-desc">Track deployment progress and resource health in real-time</div>
            </div>
        </div>

        <h2>🛡️ Named Systems</h2>
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">☠️</div>
                <div class="feature-title">Reaper Engine</div>
                <div class="feature-desc">Configure in place - deploy anywhere with Ansible playbooks for vulnerability injection</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🚀</div>
                <div class="feature-title">Updock Player Access</div>
                <div class="feature-desc">Browser-based RDP/SSH access to lab VMs via Guacamole gateway</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🛡️</div>
                <div class="feature-title">WhiteKnight Validation</div>
                <div class="feature-desc">Automated security validation and compliance checking for labs</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">♙</div>
                <div class="feature-title">WhitePawn Monitoring</div>
                <div class="feature-desc">Continuous deployment monitoring with drift detection and alerting</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🧠</div>
                <div class="feature-title">Overseer AI</div>
                <div class="feature-desc">Intelligent operator chat with Claude 3.5 Sonnet + GPT-4o integration</div>
            </div>
        </div>

        <h2>✅ Active Services</h2>
        <div class="feature-grid">
            <div class="feature-card active">
                <div class="feature-icon">🔐</div>
                <div class="feature-title">Role-Based Access Control <span class="badge badge-active">Active</span></div>
                <div class="feature-desc">Granular permissions with Admin, Architect, Engineer, and Observer roles</div>
            </div>
            <div class="feature-card active">
                <div class="feature-icon">🔒</div>
                <div class="feature-title">HashiCorp Vault <span class="badge badge-active">Active</span></div>
                <div class="feature-desc">Centralized secrets management for credentials, API keys, and tokens</div>
            </div>
            <div class="feature-card active">
                <div class="feature-icon">📖</div>
                <div class="feature-title">Documented API <span class="badge badge-active">Active</span></div>
                <div class="feature-desc">Interactive OpenAPI documentation with full schema validation</div>
            </div>
            <div class="feature-card active">
                <div class="feature-icon">🧪</div>
                <div class="feature-title">Test Pipeline <span class="badge badge-active">Active</span></div>
                <div class="feature-desc">Comprehensive pytest suite with 78 tests passing</div>
            </div>
        </div>

        <h2>📅 Build History</h2>
        <div class="timeline">
            <div class="timeline-item">
                <div class="timeline-date">November 19, 2024</div>
                <div class="timeline-title">Project Inception</div>
                <div class="timeline-desc">Initial architecture design, FastAPI backend, agent framework</div>
            </div>
            <div class="timeline-item">
                <div class="timeline-date">November 20-21, 2024</div>
                <div class="timeline-title">Platform Integration</div>
                <div class="timeline-desc">Proxmox, ESXi, AWS, Azure clients implemented. Template-based deployment working.</div>
            </div>
            <div class="timeline-item">
                <div class="timeline-date">November 22-24, 2024</div>
                <div class="timeline-title">RAG System & Network Discovery</div>
                <div class="timeline-desc">5,000+ document RAG index built. Cisco switch discovery. Mailcow integration.</div>
            </div>
            <div class="timeline-item">
                <div class="timeline-date">November 25-27, 2024</div>
                <div class="timeline-title">Security & Canvas</div>
                <div class="timeline-desc">HashiCorp Vault integration. Session management. Visual lab designer with ReactFlow.</div>
            </div>
            <div class="timeline-item">
                <div class="timeline-date">November 28-29, 2024</div>
                <div class="timeline-title">MVP & Player Portal</div>
                <div class="timeline-desc">Updock player access. Contextual help system. Reaper vulnerability engine.</div>
            </div>
            <div class="timeline-item">
                <div class="timeline-date">November 30, 2024</div>
                <div class="timeline-title">v0.7.0 API Refactor</div>
                <div class="timeline-desc">API versioning (/api/v1/*), 78 integration tests, all platforms connected.</div>
            </div>
        </div>

        <h2>📦 Package Installation</h2>
        <p>Glassdome is a proper Python package that can be installed for development or production use:</p>

        <h3>Development Installation</h3>
        <div class="code-block">
cd /home/nomad/glassdome
pip install -e .
        </div>

        <h3>Start the Server</h3>
        <div class="code-block">
# Export environment variables (CRITICAL)
export $(grep -v '^#' .env | xargs)

# Activate virtual environment
source venv/bin/activate

# Start backend server
python -m uvicorn glassdome.main:app --host 0.0.0.0 --port 8011
        </div>

        <h3>Start Frontend</h3>
        <div class="code-block">
cd frontend
npm install
npm run dev
        </div>

        <h3>Run Tests</h3>
        <div class="code-block">
python -m pytest tests/ -v
# 78 passed, 3 skipped
        </div>

        <h2>🏗️ Technology Stack</h2>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background: #f8f9fa;">
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #00d4ff;">Layer</th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #00d4ff;">Technology</th>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">Backend</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">FastAPI (Python 3.11+)</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">Database</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">PostgreSQL (async via asyncpg)</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">Cache/Queue</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">Redis + Celery</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">Frontend</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">React 18 + Vite</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">Secrets</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">HashiCorp Vault</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">Auth</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">JWT tokens + RBAC</td>
            </tr>
        </table>

        <h2>📚 Documentation</h2>
        <p>Comprehensive documentation is available in the <code>docs/</code> directory:</p>
        <ul>
            <li><strong>AGENT_CONTEXT.md</strong> - Agent context and capabilities</li>
            <li><strong>ARCHITECTURE.md</strong> - System architecture overview</li>
            <li><strong>API.md</strong> - REST API reference</li>
            <li><strong>REAPER_SYSTEM.md</strong> - Vulnerability injection system</li>
            <li><strong>RAG_USAGE.md</strong> - RAG knowledge system</li>
            <li><strong>session_logs/</strong> - Development history</li>
        </ul>

        <div class="footer">
            <p>Built with ❤️ by <strong>Brett Turner</strong> | November 2025</p>
            <p>🔮 Glassdome - The Future of Cyber Range Operations</p>
            <p style="color: #aaa; font-size: 11px;">Sent via Glassdome Mailcow Agent • {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </div>
</body>
</html>'''


def get_welcome_email_text():
    """Generate plain text version of welcome email."""
    return f'''
================================================================================
                           🔮 GLASSDOME
                   Autonomous Cyber Range Operations
                           Version 0.7.0
================================================================================

Welcome to Glassdome – an AI-powered agentic framework for deploying 
cybersecurity training lab environments in minutes, not hours.

================================================================================
🎯 WHAT IS GLASSDOME?
================================================================================

Glassdome is an Agentic Cyber Range Deployment Framework that autonomously 
deploys complex cybersecurity lab environments across multiple virtualization 
platforms. It combines intelligent agents with infrastructure-as-code to create 
a seamless deployment experience.

Key Stats:
- 4 Platforms (Proxmox, ESXi, AWS, Azure)
- 15 Core Features
- 47s Average Deployment Time
- 78 Tests Passing

================================================================================
✨ CORE FEATURES
================================================================================

🤖 Autonomous Agents - AI-powered deployment agents
🎨 Visual Lab Designer - Drag-and-drop canvas with ReactFlow
☁️ Multi-Platform - Deploy to Proxmox, Azure, AWS, or hybrid
⚡ Rapid Deployment - Design to deployed lab in minutes
🔄 Orchestration - Dependency management and parallel execution
📊 Real-time Monitoring - Track progress and resource health

================================================================================
🛡️ NAMED SYSTEMS
================================================================================

☠️ Reaper Engine - Vulnerability injection via Ansible playbooks
🚀 Updock Player Access - Browser-based RDP/SSH via Guacamole
🛡️ WhiteKnight Validation - Automated security validation
♙ WhitePawn Monitoring - Continuous monitoring with drift detection
🧠 Overseer AI - Intelligent chat with Claude 3.5 + GPT-4o

================================================================================
✅ ACTIVE SERVICES
================================================================================

🔐 Role-Based Access Control [ACTIVE] - Admin, Architect, Engineer, Observer
🔒 HashiCorp Vault [ACTIVE] - Centralized secrets management
📖 Documented API [ACTIVE] - Interactive OpenAPI documentation
🧪 Test Pipeline [ACTIVE] - 78 pytest tests passing

================================================================================
📅 BUILD HISTORY
================================================================================

Nov 19, 2024 - Project Inception
  Initial architecture, FastAPI backend, agent framework

Nov 20-21, 2024 - Platform Integration
  Proxmox, ESXi, AWS, Azure clients. Template-based deployment.

Nov 22-24, 2024 - RAG System & Network Discovery
  5,000+ document RAG index. Cisco switch discovery. Mailcow.

Nov 25-27, 2024 - Security & Canvas
  HashiCorp Vault. Session management. Visual lab designer.

Nov 28-29, 2024 - MVP & Player Portal
  Updock player access. Contextual help. Reaper engine.

Nov 30, 2024 - v0.7.0 API Refactor
  API versioning (/api/v1/*), 78 tests, all platforms connected.

================================================================================
📦 PACKAGE INSTALLATION
================================================================================

Development Installation:
  cd /home/nomad/glassdome
  pip install -e .

Start the Server:
  export $(grep -v '^#' .env | xargs)
  source venv/bin/activate
  python -m uvicorn glassdome.main:app --host 0.0.0.0 --port 8011

Start Frontend:
  cd frontend
  npm install
  npm run dev

Run Tests:
  python -m pytest tests/ -v
  # 78 passed, 3 skipped

================================================================================
🏗️ TECHNOLOGY STACK
================================================================================

Backend:     FastAPI (Python 3.11+)
Database:    PostgreSQL (async via asyncpg)
Cache/Queue: Redis + Celery
Frontend:    React 18 + Vite
Secrets:     HashiCorp Vault
Auth:        JWT tokens + RBAC

================================================================================
📚 DOCUMENTATION
================================================================================

Located in docs/ directory:
- AGENT_CONTEXT.md - Agent context and capabilities
- ARCHITECTURE.md - System architecture overview
- API.md - REST API reference
- REAPER_SYSTEM.md - Vulnerability injection system
- RAG_USAGE.md - RAG knowledge system
- session_logs/ - Development history

================================================================================

Built with ❤️ by Brett Turner | November 2025

🔮 Glassdome - The Future of Cyber Range Operations

Sent via Glassdome Mailcow Agent • {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
'''


async def send_welcome_email():
    """Send welcome email to new team members."""
    
    # Load secure settings
    settings = get_secure_settings()
    
    if not settings.mail_api:
        print("❌ Mailcow API token not configured. Check .env file.")
        print("Required: MAIL_API=your-bearer-token")
        return False
    
    # Configure Mailcow client
    api_url = settings.mailcow_api_url or f"https://mail.{settings.mailcow_domain}"
    
    client = MailcowClient(
        api_url=api_url,
        api_token=settings.mail_api,
        domain=settings.mailcow_domain,
        verify_ssl=settings.mailcow_verify_ssl
    )
    
    # Email configuration
    sender = f"glassdome-ai@{settings.mailcow_domain}"
    to_addresses = [
        "leah.salzman@wwt.com",
        "zachery.turpen@wwt.com"
    ]
    cc_addresses = [
        "brett.turner@wwt.com"
    ]
    subject = "Welcome to Glassdome - Autonomous Cyber Range Operations"
    
    print("=" * 70)
    print("🔮 Glassdome Welcome Email")
    print("=" * 70)
    print(f"From: {sender}")
    print(f"To: {', '.join(to_addresses)}")
    print(f"CC: {', '.join(cc_addresses)}")
    print(f"Subject: {subject}")
    print("-" * 70)
    
    # Send email via API
    result = client.send_email(
        mailbox=sender,
        to_addresses=to_addresses,
        subject=subject,
        body=get_welcome_email_text(),
        html_body=get_welcome_email_html(),
        cc=cc_addresses,
        use_api=True
    )
    
    if result.get('success'):
        print("✅ Welcome email sent successfully!")
        print(f"   Sent at: {result.get('sent_at')}")
        print(f"   Method: {result.get('method', 'api')}")
        return True
    else:
        print(f"❌ Failed to send email: {result.get('error')}")
        
        # Try SMTP fallback with password
        if settings.glassdome_ai_password:
            print("\n⏳ Attempting SMTP fallback...")
            result = client.send_email(
                mailbox=sender,
                password=settings.glassdome_ai_password,
                to_addresses=to_addresses,
                subject=subject,
                body=get_welcome_email_text(),
                html_body=get_welcome_email_html(),
                cc=cc_addresses,
                use_api=False
            )
            
            if result.get('success'):
                print("✅ Welcome email sent successfully via SMTP!")
                return True
            else:
                print(f"❌ SMTP also failed: {result.get('error')}")
        
        return False


if __name__ == "__main__":
    success = asyncio.run(send_welcome_email())
    sys.exit(0 if success else 1)

