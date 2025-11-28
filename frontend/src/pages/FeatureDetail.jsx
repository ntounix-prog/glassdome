/**
 * Featuredetail page component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

import { useParams, useNavigate } from 'react-router-dom'
import '../styles/FeatureDetail.css'

const FEATURES = {
  agents: {
    icon: '🤖',
    title: 'Autonomous Agents',
    subtitle: 'AI-powered deployment agents handle complex orchestration automatically',
    
    description: `Glassdome's agent framework provides autonomous, specialized agents for deployment, 
    research, and vulnerability injection. Each agent operates independently with shared logic for 
    validation, status tracking, and error handling.`,
    
    implemented: [
      {
        name: 'Ubuntu Installer Agent',
        status: 'working',
        description: 'Deploys Ubuntu VMs across all 4 platforms (Proxmox, ESXi, AWS, Azure) using cloud-init',
        details: ['Ubuntu 22.04 & 20.04 support', 'SSH key injection', 'Package installation', 'Static/DHCP networking']
      },
      {
        name: 'Windows Installer Agent', 
        status: 'partial',
        description: 'Deploys Windows VMs - fully working on cloud, template-based on-prem',
        details: ['Windows Server 2022', 'AWS/Azure via AMI', 'Proxmox via templates', 'RDP auto-enabled']
      },
      {
        name: 'Overseer Agent',
        status: 'working',
        description: 'Master orchestration agent with chat interface and tool execution',
        details: ['Claude 3.5 Sonnet powered', 'Infrastructure tools', 'Mailcow integration', 'Context-aware responses']
      },
      {
        name: 'Guest Agent Fixer',
        status: 'working', 
        description: 'Automatically repairs QEMU guest agent issues on VMs',
        details: ['Auto-detection', 'Service restart', 'Driver installation']
      },
      {
        name: 'Mailcow Agent',
        status: 'working',
        description: 'Manages Mailcow email server for Overseer communications',
        details: ['Email sending', 'Inbox management', 'Notification routing']
      },
      {
        name: 'Reaper Agent',
        status: 'partial',
        description: 'Vulnerability injection - WEAK SSH patterns operational',
        details: ['WEAK SSH injection ✓', 'Seed patterns operational', 'SQL injection (planned)', 'XSS (planned)', 'SMB exploits (planned)']
      },
      {
        name: 'Research Agent',
        status: 'partial',
        description: 'AI-powered CVE analysis via Range AI + Overseer GPT-4o',
        details: ['GPT-4o via Overseer ✓', 'Range AI integration ✓', 'Multi-LLM (expanding)', 'NVD integration (planned)']
      }
    ],
    
    roadmap: [
      {
        name: 'Kali/Parrot Installers',
        priority: 'medium',
        description: 'Security distro deployment agents',
        timeline: 'Q1 2025',
        details: ['Pre-configured tools', 'Attack console setup', 'Network integration']
      }
    ],
    
    architecture: `
┌─────────────────────────────────────┐
│          BaseAgent (Abstract)        │
├─────────────────────────────────────┤
│ - agent_id                          │
│ - status (IDLE → RUNNING → DONE)    │
│ - validate(task)                    │
│ - execute(task) [abstract]          │
└─────────────────┬───────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ↓             ↓             ↓
┌────────┐  ┌──────────┐  ┌──────────┐
│Ubuntu  │  │ Windows  │  │ Overseer │
│Install │  │ Install  │  │ Monitor  │
└────────┘  └──────────┘  └──────────┘
    `,
    
    codeLocation: 'glassdome/agents/',
    files: ['base.py', 'ubuntu_installer.py', 'windows_installer.py', 'overseer.py', 'mailcow_agent.py']
  },

  designer: {
    icon: '🎨',
    title: 'Drag & Drop Lab Design',
    subtitle: 'Visual lab designer with intuitive drag-and-drop interface',
    
    description: `The Lab Canvas provides a visual, node-based editor for designing complex 
    cybersecurity lab environments. Drag VMs, firewalls, and networks onto the canvas, 
    connect them, and deploy with a single click.`,
    
    implemented: [
      {
        name: 'Visual Canvas',
        status: 'working',
        description: 'React Flow-based node editor with zoom, pan, and selection',
        details: ['Infinite canvas', 'Grid snapping', 'Multi-select', 'Keyboard shortcuts']
      },
      {
        name: 'Element Library',
        status: 'working',
        description: 'Drag VM templates, firewalls, and network elements onto the canvas',
        details: ['pfSense firewall', 'Kali Linux', 'Metasploitable', 'Ubuntu Server', 'Windows Server']
      },
      {
        name: 'Connection Wiring',
        status: 'working',
        description: 'Connect nodes to define network topology and dependencies',
        details: ['Edge drawing', 'Port selection', 'Visual validation']
      },
      {
        name: 'Save/Load Labs',
        status: 'working',
        description: 'Persist lab designs to database for reuse',
        details: ['Name and description', 'Load saved designs', 'Duplicate labs']
      },
      {
        name: 'One-Click Deploy',
        status: 'working',
        description: 'Deploy entire lab design to Proxmox with status tracking',
        details: ['Deployment status panel', 'Real-time logs', 'Error reporting']
      }
    ],
    
    roadmap: [
      {
        name: 'Scenario Templates',
        priority: 'high',
        description: 'Pre-built lab scenarios for common training exercises',
        timeline: 'Q1 2025',
        details: ['Web App Pentest', 'Active Directory Attack', 'Network Forensics', 'CTF Challenges']
      },
      {
        name: 'Custom Element Builder',
        priority: 'medium',
        description: 'Create custom VM types with specific configurations',
        timeline: 'Q2 2025',
        details: ['Custom icons', 'Pre-installed packages', 'Network configs']
      },
      {
        name: 'Collaboration Mode',
        priority: 'low',
        description: 'Multiple architects designing simultaneously',
        timeline: 'Q3 2025',
        details: ['Real-time cursors', 'Lock regions', 'Version history']
      }
    ],
    
    architecture: `
┌─────────────────────────────────────┐
│           Lab Canvas (React)         │
├─────────────────────────────────────┤
│  ┌──────────┐  ┌──────────────────┐ │
│  │ Element  │  │   React Flow     │ │
│  │ Palette  │→→│   Canvas Area    │ │
│  └──────────┘  └────────┬─────────┘ │
│                         ↓           │
│  ┌──────────────────────────────┐   │
│  │  Deployment Status Panel     │   │
│  │  [████████░░] 80% Complete   │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
    `,
    
    codeLocation: 'frontend/src/pages/',
    files: ['LabCanvas.jsx', 'LabCanvas.css', 'NetworkMap.jsx']
  },

  platforms: {
    icon: '☁️',
    title: 'Multi-Platform Deployment',
    subtitle: 'Deploy to Proxmox, Azure, AWS, or hybrid environments',
    
    description: `Glassdome abstracts away platform differences with a unified PlatformClient 
    interface. Write once, deploy anywhere - whether on-premises with Proxmox/ESXi or in the 
    cloud with AWS/Azure.`,
    
    implemented: [
      {
        name: 'Proxmox VE',
        status: 'working',
        description: 'Primary on-premises platform with full feature support',
        details: [
          '2-node cluster (pve01/pve02)',
          'Template cloning with cloud-init',
          'VLAN-aware networking',
          'Live VM migration',
          'TrueNAS NFS shared storage',
          '10G dual-path SAN'
        ]
      },
      {
        name: 'VMware ESXi',
        status: 'working',
        description: 'Direct ESXi API integration (no vCenter required)',
        details: ['VMDK templates', 'NoCloud ISO for config', 'Port group networking']
      },
      {
        name: 'AWS EC2',
        status: 'working',
        description: 'Amazon Web Services with on-demand instances',
        details: ['EC2 instances', 'VPC networking', 'Security groups', 'ARM64/x86_64 AMIs']
      },
      {
        name: 'Azure VMs',
        status: 'working',
        description: 'Microsoft Azure virtual machines',
        details: ['Resource groups', 'VNets/Subnets', 'NSG firewalls', 'Custom data injection']
      }
    ],
    
    roadmap: [
      {
        name: 'Google Cloud Platform',
        priority: 'medium',
        description: 'GCP Compute Engine support',
        timeline: 'Q2 2025',
        details: ['GCE instances', 'VPC networking', 'Service accounts']
      },
      {
        name: 'Kubernetes',
        priority: 'low',
        description: 'Container-based lab environments',
        timeline: 'Q3 2025',
        details: ['Pod deployments', 'Network policies', 'Ephemeral labs']
      },
      {
        name: 'Hybrid Orchestration',
        priority: 'high',
        description: 'Single lab spanning multiple platforms',
        timeline: 'Q1 2025',
        details: ['Cross-platform networking', 'VPN tunnels', 'Unified management']
      }
    ],
    
    architecture: `
┌─────────────────────────────────────┐
│      PlatformClient (Abstract)       │
├─────────────────────────────────────┤
│ + create_vm(config) → VM            │
│ + delete_vm(id)                     │
│ + get_vm_status(id) → Status        │
│ + list_vms() → List[VM]             │
│ + clone_vm(template, config)        │
└─────────────────┬───────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    ↓             ↓             ↓             ↓
┌────────┐  ┌──────────┐  ┌────────┐  ┌────────┐
│Proxmox │  │   ESXi   │  │  AWS   │  │ Azure  │
│proxmoxer│  │ pyvmomi │  │ boto3  │  │azure-* │
└────────┘  └──────────┘  └────────┘  └────────┘
    `,
    
    codeLocation: 'glassdome/platforms/',
    files: ['base.py', 'proxmox_client.py', 'esxi_client.py', 'aws_client.py', 'azure_client.py']
  },

  deployment: {
    icon: '⚡',
    title: 'Rapid Deployment',
    subtitle: 'Go from design to deployed lab in minutes, not hours',
    
    description: `Glassdome uses template cloning, hot spare pools, and parallel execution 
    to achieve sub-5-minute deployment times for complex multi-VM labs. No more waiting 
    hours for manual setup.`,
    
    implemented: [
      {
        name: 'Template Cloning',
        status: 'working',
        description: 'Clone pre-built templates instead of installing from ISO',
        details: [
          'Ubuntu 22.04 template (9001)',
          'pfSense firewall template (9020)', 
          'Kali Linux template (9002)',
          'Metasploitable template (9030)',
          '2-3 min clone time vs 30+ min install'
        ]
      },
      {
        name: 'Cloud-Init Configuration',
        status: 'working',
        description: 'Automatic VM configuration on first boot',
        details: ['Hostname', 'SSH keys', 'Network settings', 'Package installation']
      },
      {
        name: 'QEMU Guest Agent',
        status: 'working',
        description: 'Live VM configuration without reboots',
        details: ['IP discovery', 'Live interface config', 'Status monitoring']
      },
      {
        name: 'Hot Spare Pool',
        status: 'working',
        description: 'Pre-cloned VMs ready for instant deployment',
        details: ['Background replenishment', 'Per-template pools', 'Priority queue']
      }
    ],
    
    roadmap: [
      {
        name: 'Parallel VM Deployment',
        priority: 'high',
        description: 'Deploy all lab VMs simultaneously',
        timeline: 'Q1 2025',
        details: ['Up to 10 concurrent clones', 'Dependency ordering', '2x speed improvement']
      },
      {
        name: 'Pre-warming',
        priority: 'medium',
        description: 'Anticipate deployments and pre-clone VMs',
        timeline: 'Q2 2025',
        details: ['Usage patterns', 'Scheduled labs', 'Resource reservation']
      },
      {
        name: 'Incremental Snapshots',
        priority: 'low',
        description: 'Clone only differences from base template',
        timeline: 'Q3 2025',
        details: ['Linked clones', 'Storage efficiency', 'Faster cloning']
      }
    ],
    
    architecture: `
┌─────────────────────────────────────┐
│         Deployment Pipeline          │
├─────────────────────────────────────┤
│                                     │
│  [Canvas Design]                    │
│       ↓                             │
│  [Parse Nodes/Edges]                │
│       ↓                             │
│  [Hot Spare Check]──→[Clone Fresh]  │
│       ↓                             │
│  [Configure Cloud-Init]             │
│       ↓                             │
│  [Start VM]                         │
│       ↓                             │
│  [Wait for Guest Agent]             │
│       ↓                             │
│  [Live Network Config]              │
│       ↓                             │
│  [Register in Lab Registry]         │
│                                     │
└─────────────────────────────────────┘

Target Times:
• Single VM: 2-3 minutes
• 5-VM Lab: 3-5 minutes (parallel)
• 9-VM Scenario: < 5 minutes
    `,
    
    codeLocation: 'glassdome/api/',
    files: ['canvas_deploy.py', 'labs.py']
  },

  orchestration: {
    icon: '🔄',
    title: 'Orchestration Engine',
    subtitle: 'Complex dependency management and parallel execution',
    
    description: `The orchestration layer coordinates complex multi-VM, multi-network deployments. 
    It handles dependency resolution, parallel execution, failure rollback, and real-time 
    progress updates via WebSocket.`,
    
    implemented: [
      {
        name: 'Network Creation',
        status: 'working',
        description: 'VLAN-aware networking with isolated lab environments',
        details: [
          'Auto VLAN ID assignment (100-999)',
          'pfSense as lab gateway',
          'DHCP for lab VMs',
          'Management access via WAN'
        ]
      },
      {
        name: 'Dependency Resolution',
        status: 'working',
        description: 'Deploy VMs in correct order based on dependencies',
        details: ['pfSense first', 'Then lab VMs', 'Network before VMs']
      },
      {
        name: 'Celery Task Queue',
        status: 'working',
        description: 'Distributed task execution with Redis broker',
        details: [
          'Orchestrator workers (8 threads)',
          'Reaper workers (8 threads)',
          'WhiteKnight validation',
          'WhitePawn monitoring'
        ]
      },
      {
        name: 'State Tracking',
        status: 'working',
        description: 'PostgreSQL persistence of deployment state',
        details: ['Deployed VMs table', 'Network definitions', 'Lab history']
      }
    ],
    
    roadmap: [
      {
        name: 'Scenario YAML',
        priority: 'high',
        description: 'Define complex scenarios in declarative YAML',
        timeline: 'Q1 2025',
        details: ['Schema validation', 'Variable substitution', 'Reusable modules']
      },
      {
        name: 'Rollback on Failure',
        priority: 'high',
        description: 'Automatic cleanup when deployment fails',
        timeline: 'Q1 2025',
        details: ['VM deletion', 'Network cleanup', 'State reset']
      },
      {
        name: 'Parallel Execution',
        priority: 'high',
        description: 'Deploy independent VMs simultaneously',
        timeline: 'Q1 2025',
        details: ['DAG-based scheduling', 'Resource limits', 'Progress aggregation']
      }
    ],
    
    architecture: `
┌─────────────────────────────────────┐
│        Orchestration Engine          │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐   │
│  │     Scenario Definition       │   │
│  │  (YAML / Canvas / API)        │   │
│  └──────────────┬───────────────┘   │
│                 ↓                   │
│  ┌──────────────────────────────┐   │
│  │     Dependency Resolver       │   │
│  │  [A] → [B] → [C]              │   │
│  │    ↘   ↓   ↙                 │   │
│  │      [D]                      │   │
│  └──────────────┬───────────────┘   │
│                 ↓                   │
│  ┌──────────────────────────────┐   │
│  │   Celery Task Queue (Redis)   │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐     │   │
│  │  │ W1  │ │ W2  │ │ W3  │     │   │
│  │  └─────┘ └─────┘ └─────┘     │   │
│  └──────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
    `,
    
    codeLocation: 'glassdome/orchestration/',
    files: ['engine.py', 'lab_orchestrator.py', 'workers/orchestrator.py']
  },

  monitoring: {
    icon: '📊',
    title: 'Real-time Monitoring',
    subtitle: 'Track deployment progress and resource health in real-time',
    
    description: `The Lab Registry provides a central source of truth for all deployed resources. 
    Platform agents poll infrastructure at tiered intervals, publishing state changes to Redis 
    Pub/Sub for real-time UI updates via WebSocket.`,
    
    implemented: [
      {
        name: 'Lab Registry',
        status: 'working',
        description: 'Central Redis-backed state store for all resources',
        details: [
          'Resource types: VM, Template, Network, Host',
          'Event pub/sub for state changes',
          'WebSocket streaming to frontend'
        ]
      },
      {
        name: 'Proxmox Agent',
        status: 'working',
        description: 'Polls Proxmox clusters for VM state changes',
        details: ['10-second polling interval', 'IP discovery via guest agent', 'Deleted VM detection']
      },
      {
        name: 'Unifi Agent',
        status: 'working',
        description: 'Discovers VM IPs via Unifi DHCP leases',
        details: ['MAC → IP mapping', 'pfSense WAN discovery', 'Client tracking']
      },
      {
        name: 'Dashboard Status',
        status: 'working',
        description: 'Real-time resource counts and health on dashboard',
        details: ['Registry status', 'Agent count', 'Drift alerts']
      },
      {
        name: 'Lab Monitor Page',
        status: 'working',
        description: 'Dedicated page for real-time lab state',
        details: ['Resource list', 'Event stream', 'Lab snapshots']
      }
    ],
    
    roadmap: [
      {
        name: 'Drift Detection',
        priority: 'high',
        description: 'Detect when actual state differs from desired state',
        timeline: 'Q1 2025',
        details: ['Name drift', 'State drift', 'IP changes', 'Auto-reconciliation']
      },
      {
        name: 'Self-Healing',
        priority: 'high',
        description: 'Automatically fix detected drift',
        timeline: 'Q1 2025',
        details: ['VM restart', 'Name correction', 'Network repair']
      },
      {
        name: 'Proxmox Webhooks',
        priority: 'medium',
        description: 'Sub-second updates via Proxmox notification endpoints',
        timeline: 'Q2 2025',
        details: ['<1s latency', 'Reduced polling', 'Event-driven']
      },
      {
        name: 'TrueNAS Agent',
        priority: 'low',
        description: 'Monitor storage health and capacity',
        timeline: 'Q2 2025',
        details: ['Pool status', 'Disk health', 'Capacity alerts']
      }
    ],
    
    architecture: `
┌─────────────────────────────────────────────┐
│              Lab Registry (Redis)            │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐    │
│  │  VMs    │ │Templates│ │  Networks   │    │
│  │(Tier 1) │ │(Tier 2) │ │  (Tier 1)   │    │
│  └────┬────┘ └────┬────┘ └──────┬──────┘    │
└───────┼──────────┼──────────────┼───────────┘
        ↑          ↑              ↑
        │    Event Pub/Sub (Redis)│
    ┌───┴───┐  ┌───┴───┐    ┌─────┴─────┐
    │Proxmox│  │ Unifi │    │ TrueNAS   │
    │ Agent │  │ Agent │    │  Agent    │
    │(10s)  │  │(15s)  │    │  (60s)    │
    └───────┘  └───────┘    └───────────┘
                  ↓
        ┌─────────────────┐
        │  WebSocket API  │
        │  /ws/events     │
        └────────┬────────┘
                 ↓
        ┌─────────────────┐
        │  React Frontend │
        │  (Real-time UI) │
        └─────────────────┘
    `,
    
    codeLocation: 'glassdome/registry/',
    files: ['core.py', 'models.py', 'agents/proxmox_agent.py', 'agents/unifi_agent.py']
  },

  reaper: {
    icon: '☠️',
    title: 'Reaper Vulnerability Engine',
    subtitle: 'Configure in place - deploy anywhere, same lab state every time',
    
    description: `Reaper solves the cross-platform migration problem by making lab STATE 
    platform-independent. Instead of migrating VMs (impossible between Proxmox and AWS), 
    you deploy fresh VMs anywhere and Reaper configures them identically using Ansible playbooks. 
    The playbooks ARE the lab definition - not the VMs themselves.`,
    
    implemented: [
      {
        name: 'Native Ansible Support',
        status: 'working',
        description: 'Engineers write standard Ansible playbooks - Reaper executes them on any platform',
        details: [
          'Direct playbook import - drop in your .yml files',
          'AnsibleExecutor wraps ansible-playbook CLI natively',
          'AnsibleBridge auto-generates inventory from deployed VMs',
          'Full support: extra vars, tags, limits, roles',
          'No special syntax - standard Ansible format'
        ]
      },
      {
        name: 'Vulnerability Playbooks',
        status: 'working',
        description: 'Pre-built Ansible playbooks for common training scenarios',
        details: [
          'web/inject_sqli.yml - DVWA SQL injection',
          'web/inject_xss.yml - Cross-site scripting',
          'system/weak_ssh.yml - Weak credentials',
          'system/weak_sudo.yml - Privilege escalation',
          'network/open_ports.yml - Exposed services'
        ]
      },
      {
        name: 'OS-Specific Agents',
        status: 'working',
        description: 'Specialized agents for Linux, Windows, and macOS targets',
        details: [
          'LinuxReaperAgent - SSH + Ansible',
          'WindowsReaperAgent - WinRM + Ansible',
          'MacReaperAgent - SSH + Ansible',
          'Auto-detection of target OS'
        ]
      },
      {
        name: 'Mission Planner',
        status: 'working',
        description: 'Rule-based planning for multi-phase vulnerability injection',
        details: [
          'Discovery phase - gather target facts',
          'Baseline phase - inject standard vulnerabilities',
          'Specialized phase - OS/service-specific exploits',
          'Verification phase - confirm exploitability'
        ]
      },
      {
        name: 'Celery Task Queue',
        status: 'working',
        description: 'Distributed execution via Redis-backed task queue',
        details: [
          'Async playbook execution',
          'Parallel multi-VM injection',
          'Progress tracking and logging'
        ]
      },
      {
        name: 'Exploit Import/Export',
        status: 'working',
        description: 'Engineers can build exploits offline and import via JSON or reference Ansible playbooks directly',
        details: [
          'JSON bulk import - upload exploit definitions',
          'Direct Ansible playbook references (ansible_playbook field)',
          'Export all exploits for backup/sharing',
          'Template download for offline development',
          'Standard Ansible format - no special syntax needed'
        ]
      }
    ],
    
    roadmap: [
      {
        name: 'Windows Vulnerability Library',
        priority: 'high',
        description: 'Expand Windows-specific vulnerability playbooks',
        timeline: 'Q1 2025',
        details: ['SMB exploits', 'RDP weaknesses', 'Unpatched services', 'Privilege escalation']
      },
      {
        name: 'CVE-Based Injection',
        priority: 'high',
        description: 'Install specific CVE vulnerabilities by ID',
        timeline: 'Q1 2025',
        details: ['CVE database lookup', 'Automated PoC installation', 'Version-specific packages']
      },
      {
        name: 'Lab Migration API',
        priority: 'medium',
        description: 'Export/import lab configurations as portable bundles',
        timeline: 'Q2 2025',
        details: ['Lab definition export', 'Playbook bundling', 'One-click reimport on any platform']
      },
      {
        name: 'Live Verification Dashboard',
        priority: 'medium',
        description: 'Real-time exploit verification with WhiteKnight integration',
        timeline: 'Q2 2025',
        details: ['Auto-scan after injection', 'Exploitability confirmation', 'Training readiness score']
      }
    ],
    
    architecture: `
┌─────────────────────────────────────────────────────────────────┐
│                    "CONFIGURE IN PLACE"                          │
│         The Key Insight: Playbooks ARE the Lab State             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  LAB DEFINITION │     Ansible playbooks define vulnerabilities,
│  (YAML/Canvas)  │     configurations, users, packages - everything
└────────┬────────┘     needed to recreate the lab state.
         │
         ▼
┌─────────────────┐     AnsibleBridge auto-generates inventory
│ AnsibleBridge   │     from any deployed VMs, regardless of
│ (VM → Inventory)│     which platform they run on.
└────────┬────────┘
         │
    ┌────┴────┬────────────┐
    ▼         ▼            ▼
┌───────┐ ┌───────┐ ┌──────────┐
│Proxmox│ │  AWS  │ │  Azure   │     Same playbooks execute on
│  VMs  │ │  EC2  │ │   VMs    │     ANY platform's VMs.
└───┬───┘ └───┬───┘ └────┬─────┘
    │         │          │
    └─────────┼──────────┘
              ▼
┌─────────────────────────┐
│   AnsibleExecutor       │     Wraps ansible-playbook CLI,
│   (Run Playbooks)       │     passes extra vars, parses results.
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│   IDENTICAL LAB STATE   │     🎯 The Goal: Same training
│   • Same vulnerabilities│        environment everywhere.
│   • Same credentials    │
│   • Same scenarios      │
└─────────────────────────┘

Why This Matters:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• VM migration between platforms is IMPOSSIBLE
  (Proxmox qcow2 ≠ AWS AMI ≠ Azure VHD)

• Lab MIGRATION becomes lab RE-CREATION
  (Deploy fresh VMs + run same playbooks = same lab)

• VMs are cattle, not pets
  (Destroy and rebuild at will)
    `,
    
    codeLocation: 'glassdome/reaper/',
    files: [
      'planner.py',
      'agents/base.py', 
      'agents/linux_agent.py',
      'agents/windows_agent.py',
      'models.py'
    ]
  }
}

function StatusBadge({ status }) {
  const colors = {
    working: 'badge-success',
    partial: 'badge-warning',
    planned: 'badge-info'
  }
  const labels = {
    working: '✓ Working',
    partial: '⚠ Partial',
    planned: '📋 Planned'
  }
  return <span className={`badge ${colors[status]}`}>{labels[status]}</span>
}

function PriorityBadge({ priority }) {
  const colors = {
    high: 'priority-high',
    medium: 'priority-medium',
    low: 'priority-low'
  }
  return <span className={`priority-badge ${colors[priority]}`}>{priority.toUpperCase()}</span>
}

export default function FeatureDetail() {
  const { featureId } = useParams()
  const navigate = useNavigate()
  const feature = FEATURES[featureId]

  if (!feature) {
    return (
      <div className="feature-detail">
        <div className="feature-not-found">
          <h1>Feature Not Found</h1>
          <p>The feature "{featureId}" doesn't exist.</p>
          <button onClick={() => navigate('/')}>← Back to Dashboard</button>
        </div>
      </div>
    )
  }

  return (
    <div className="feature-detail">
      <button className="back-button" onClick={() => navigate('/')}>
        ← Back to Dashboard
      </button>

      <header className="feature-header">
        <div className="feature-icon-large">{feature.icon}</div>
        <div className="feature-titles">
          <h1>{feature.title}</h1>
          <p className="feature-subtitle">{feature.subtitle}</p>
        </div>
      </header>

      <section className="feature-description">
        <p>{feature.description}</p>
      </section>

      <div className="feature-content">
        <section className="feature-section implemented">
          <h2>✅ Currently Implemented</h2>
          <div className="items-grid">
            {feature.implemented.map((item, idx) => (
              <div key={idx} className="item-card">
                <div className="item-header">
                  <h3>{item.name}</h3>
                  <StatusBadge status={item.status} />
                </div>
                <p className="item-description">{item.description}</p>
                <ul className="item-details">
                  {item.details.map((detail, i) => (
                    <li key={i}>{detail}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="feature-section roadmap">
          <h2>🗺️ Roadmap</h2>
          <div className="items-grid">
            {feature.roadmap.map((item, idx) => (
              <div key={idx} className="item-card roadmap-card">
                <div className="item-header">
                  <h3>{item.name}</h3>
                  <PriorityBadge priority={item.priority} />
                </div>
                <p className="item-description">{item.description}</p>
                <div className="timeline">📅 {item.timeline}</div>
                <ul className="item-details">
                  {item.details.map((detail, i) => (
                    <li key={i}>{detail}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="feature-section architecture">
          <h2>🏗️ Architecture</h2>
          <pre className="architecture-diagram">{feature.architecture}</pre>
        </section>

        <section className="feature-section code-location">
          <h2>📁 Code Location</h2>
          <div className="code-info">
            <p><strong>Directory:</strong> <code>{feature.codeLocation}</code></p>
            <p><strong>Key Files:</strong></p>
            <ul className="file-list">
              {feature.files.map((file, idx) => (
                <li key={idx}><code>{file}</code></li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </div>
  )
}

