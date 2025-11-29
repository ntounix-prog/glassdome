/**
 * Contextual Help System
 * Maps routes to help content for Overseer integration
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

// Help content organized by route/page
const HELP_CONTENT = {
  // Dashboard
  '/': {
    title: 'Dashboard',
    role: 'operator',
    summary: 'Main control center for Glassdome cyber range operations.',
    topics: [
      {
        title: 'Getting Started',
        content: `Welcome to Glassdome! From the dashboard you can:
• Click "Create New Lab" to design a new cyber range environment
• View system status (API, Registry, Agents, Drifts)
• Access feature pages to learn about capabilities
• Click the Demo button for an overview presentation`
      },
      {
        title: 'Feature Cards',
        content: `Each feature card links to detailed information:
• Autonomous Agents - AI-powered deployment automation
• Lab Designer - Visual drag-and-drop lab creation
• Multi-Platform - Deploy to Proxmox, AWS, Azure
• Reaper Engine - Vulnerability injection system
• Updock - Player browser-based access
• WhiteKnight - Automated validation
• WhitePawn - Continuous monitoring
• Overseer - AI assistant (that's me!)`
      },
      {
        title: 'System Status',
        content: `The status bar shows:
• Backend API - Connection to the Glassdome server
• Lab Registry - Real-time resource tracking (Redis)
• Agents - Active platform monitoring agents
• Drifts - Detected configuration differences`
      }
    ],
    quickActions: [
      { label: 'Create a lab', action: 'Navigate to /lab' },
      { label: 'Check platforms', action: 'Navigate to /platform' },
      { label: 'View deployments', action: 'Navigate to /deployments' }
    ]
  },

  // Lab Designer/Canvas
  '/lab': {
    title: 'Lab Designer',
    role: 'operator',
    summary: 'Visual canvas for designing cyber range environments.',
    topics: [
      {
        title: 'Creating a Lab',
        content: `To create a new lab:
1. Drag VM templates from the left sidebar onto the canvas
2. VMs will auto-connect - a pfSense gateway is created automatically
3. Click on a VM node to configure its settings
4. Enter a Lab Name in the header
5. Click "Deploy" to provision the environment`
      },
      {
        title: 'VM Templates',
        content: `Available templates include:
• Kali Linux - Attack/pentest workstation
• Ubuntu - General purpose Linux
• Windows Server - Domain controller, file server
• Metasploitable - Intentionally vulnerable target
• Custom templates from your Proxmox library`
      },
      {
        title: 'Networking',
        content: `Labs are automatically networked:
• Each lab gets an isolated VLAN (10.x.0.0/24)
• pfSense gateway provides NAT and DHCP
• VMs receive IPs via DHCP from pfSense
• Gateway provides internet access via NAT`
      },
      {
        title: 'Deployment',
        content: `When you click Deploy:
1. A new VLAN is allocated
2. pfSense gateway is cloned and configured
3. VMs are cloned in parallel
4. Network interfaces are configured
5. Lab is registered for monitoring`
      },
      {
        title: 'Saving & Loading',
        content: `Use the Load dropdown to:
• Save current design for later
• Load previously saved designs
• Start from a template scenario`
      }
    ],
    quickActions: [
      { label: 'Add a Kali VM', action: 'Drag Kali from sidebar' },
      { label: 'Deploy this lab', action: 'Click Deploy button' }
    ]
  },

  // Deployments
  '/deployments': {
    title: 'Deployments',
    role: 'operator',
    summary: 'View and manage all deployed lab environments.',
    topics: [
      {
        title: 'Viewing Labs',
        content: `The deployments page shows:
• All active lab deployments
• Lab status (Running, Stopped, Error)
• VM count and resource usage
• Quick actions for each lab`
      },
      {
        title: 'Lab Actions',
        content: `For each lab you can:
• View details and VM list
• Start/Stop all VMs
• Access player portal link
• Destroy the lab (cleanup)`
      },
      {
        title: 'Filtering',
        content: `Use the tabs to filter:
• All - All deployments
• Running - Active labs
• Stopped - Paused labs
• Mine - Labs you created`
      }
    ],
    quickActions: [
      { label: 'Create new lab', action: 'Navigate to /lab' }
    ]
  },

  // Platform Status
  '/platform': {
    title: 'Platform Status',
    role: 'operator',
    summary: 'Monitor connected infrastructure platforms.',
    topics: [
      {
        title: 'Connected Platforms',
        content: `Glassdome can connect to:
• Proxmox VE - On-premise virtualization
• AWS EC2 - Amazon cloud instances
• Microsoft Azure - Azure virtual machines
• VMware ESXi - Enterprise virtualization (planned)`
      },
      {
        title: 'Platform Health',
        content: `For each platform you can see:
• Connection status
• Available resources (CPU, RAM, storage)
• Active VMs and templates
• Recent activity`
      },
      {
        title: 'On-Demand Connections',
        content: `Cloud platforms (AWS, Azure) connect on-demand:
• Click "Connect" to establish session
• Credentials pulled from secrets store
• Auto-disconnect after idle timeout`
      }
    ],
    quickActions: [
      { label: 'View Proxmox VMs', action: 'Click Proxmox card' }
    ]
  },

  // Player Portal
  '/player': {
    title: 'Player Portal',
    role: 'player',
    summary: 'Entry point for trainees to join cyber range labs.',
    topics: [
      {
        title: 'Joining a Lab',
        content: `To join a lab:
1. Enter the lab code provided by your instructor
2. Click "Enter Lab" or press Enter
3. You'll see available machines in the lab lobby`
      },
      {
        title: 'Lab Codes',
        content: `Lab codes are provided by your range operator.
They typically look like: brettlab, training-01, ctf-2025
If you don't have a code, contact your instructor.`
      }
    ],
    quickActions: []
  },

  // Player Lobby
  '/player/:labId': {
    title: 'Lab Lobby',
    role: 'player',
    summary: 'Select your machine and view mission objectives.',
    topics: [
      {
        title: 'Available Machines',
        content: `Each card shows a machine you can access:
• Machine name and type (Kali, Windows, etc.)
• Status (Online, Offline, Starting)
• Click "Connect" to open the desktop`
      },
      {
        title: 'Mission Brief',
        content: `If your lab has objectives:
• Read the mission brief on the right
• Note any hints or flag formats
• Track your progress as you complete goals`
      },
      {
        title: 'Lab Timer',
        content: `Some labs have time limits:
• Timer shows remaining time
• Save your work before time expires
• Contact instructor if you need more time`
      }
    ],
    quickActions: [
      { label: 'Connect to machine', action: 'Click Connect on a card' }
    ]
  },

  // Player Session
  '/player/:labId/:vmName': {
    title: 'VM Session',
    role: 'player',
    summary: 'Full desktop access to your lab machine.',
    topics: [
      {
        title: 'Using the Desktop',
        content: `You have full access to the machine:
• Use it like a regular desktop
• Run commands, open applications
• Access the network and other lab machines`
      },
      {
        title: 'Controls',
        content: `Session controls:
• Fullscreen - Expand to full browser
• Clipboard - Copy/paste between local and remote
• Ctrl+Alt+Del - Send to remote machine
• Back - Return to lobby`
      },
      {
        title: 'Troubleshooting',
        content: `If the session doesn't connect:
• Check the machine is running (green status)
• Try refreshing the page
• Click "Open in Guacamole" for direct access
• Contact your instructor if issues persist`
      }
    ],
    quickActions: [
      { label: 'Go fullscreen', action: 'Click fullscreen button' },
      { label: 'Return to lobby', action: 'Click back button' }
    ]
  },

  // Lab Monitor
  '/monitor': {
    title: 'Lab Monitor',
    role: 'operator',
    summary: 'Real-time monitoring of all lab resources.',
    topics: [
      {
        title: 'Live Status',
        content: `Monitor shows real-time data:
• VM states across all platforms
• Network connectivity
• Resource utilization
• Event stream`
      },
      {
        title: 'Drift Detection',
        content: `WhitePawn detects drift when:
• VMs unexpectedly stop
• IPs change
• Resources go missing
• Configurations differ from expected`
      }
    ],
    quickActions: []
  },

  // WhitePawn Monitor
  '/whitepawn': {
    title: 'WhitePawn Monitoring',
    role: 'operator',
    summary: 'Deployment health and drift detection system.',
    topics: [
      {
        title: 'What is WhitePawn?',
        content: `WhitePawn continuously monitors deployed labs:
• Tracks VM power states
• Detects configuration drift
• Alerts on anomalies
• Can auto-remediate issues`
      },
      {
        title: 'Alerts',
        content: `Alert types:
• VM Offline - A VM stopped unexpectedly
• Drift Detected - Config differs from expected
• High Resource - CPU/memory threshold exceeded
• Network Issue - Connectivity problem`
      }
    ],
    quickActions: []
  },

  // Reaper
  '/reaper': {
    title: 'Reaper Engine',
    role: 'operator',
    summary: 'Vulnerability injection for realistic training scenarios.',
    topics: [
      {
        title: 'What is Reaper?',
        content: `Reaper injects real vulnerabilities into lab VMs:
• Uses Ansible playbooks for configuration
• Platform-agnostic (same vulns on any platform)
• Enables realistic offensive training`
      },
      {
        title: 'Available Vulnerabilities',
        content: `Built-in vulnerability types:
• Weak SSH - Password-based login with weak creds
• SQL Injection - Web application SQLi
• XSS - Cross-site scripting
• Privilege Escalation - Sudo misconfigurations
• Open Ports - Exposed services`
      },
      {
        title: 'Using Reaper',
        content: `To inject vulnerabilities:
1. Select target VMs in a deployed lab
2. Choose vulnerability playbooks
3. Click "Inject" to apply
4. WhiteKnight verifies exploitability`
      }
    ],
    quickActions: [
      { label: 'View exploit library', action: 'Check Exploits tab' }
    ]
  }
};

// Get help content for current route
export function getHelpForRoute(pathname) {
  // Exact match first
  if (HELP_CONTENT[pathname]) {
    return HELP_CONTENT[pathname];
  }
  
  // Pattern matching for dynamic routes
  if (pathname.startsWith('/player/') && pathname.split('/').length === 3) {
    return HELP_CONTENT['/player/:labId'];
  }
  if (pathname.startsWith('/player/') && pathname.split('/').length === 4) {
    return HELP_CONTENT['/player/:labId/:vmName'];
  }
  if (pathname.startsWith('/features/')) {
    return {
      title: 'Feature Details',
      role: 'operator',
      summary: 'Detailed information about Glassdome capabilities.',
      topics: [
        {
          title: 'Feature Pages',
          content: `Each feature page shows:
• What's currently implemented
• Status of each component
• Roadmap for future development
• Architecture diagrams
• Code locations for developers`
        }
      ],
      quickActions: [
        { label: 'Return to dashboard', action: 'Navigate to /' }
      ]
    };
  }
  
  // Default fallback
  return {
    title: 'Glassdome Help',
    role: 'all',
    summary: 'AI-powered cyber range deployment platform.',
    topics: [
      {
        title: 'Getting Help',
        content: `You can ask me anything about Glassdome!
Try questions like:
• "How do I create a new lab?"
• "What is Reaper?"
• "How do players join a lab?"`
      }
    ],
    quickActions: [
      { label: 'Go to dashboard', action: 'Navigate to /' }
    ]
  };
}

// Format help content as context for Overseer
export function getHelpContextForOverseer(pathname) {
  const help = getHelpForRoute(pathname);
  
  let context = `## Current Page: ${help.title}\n`;
  context += `${help.summary}\n\n`;
  context += `### Help Topics for This Page:\n`;
  
  help.topics.forEach(topic => {
    context += `\n**${topic.title}:**\n${topic.content}\n`;
  });
  
  if (help.quickActions.length > 0) {
    context += `\n### Quick Actions:\n`;
    help.quickActions.forEach(action => {
      context += `• ${action.label}: ${action.action}\n`;
    });
  }
  
  return context;
}

// Get all help topics for search
export function getAllHelpTopics() {
  const allTopics = [];
  
  Object.entries(HELP_CONTENT).forEach(([route, content]) => {
    content.topics.forEach(topic => {
      allTopics.push({
        route,
        pageTitle: content.title,
        role: content.role,
        title: topic.title,
        content: topic.content
      });
    });
  });
  
  return allTopics;
}

export default HELP_CONTENT;

