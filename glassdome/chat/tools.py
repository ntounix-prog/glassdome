"""
Tools module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Tool definition for LLM function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable[..., Awaitable[Dict[str, Any]]]] = None
    requires_confirmation: bool = False
    category: str = "general"


# ═══════════════════════════════════════════════════
# Tool Parameter Schemas (JSON Schema format)
# ═══════════════════════════════════════════════════

DEPLOY_LAB_PARAMS = {
    "type": "object",
    "properties": {
        "lab_name": {
            "type": "string",
            "description": "Name for the lab deployment"
        },
        "platform": {
            "type": "string",
            "enum": ["proxmox", "aws", "azure", "esxi"],
            "description": "Target platform for deployment"
        },
        "lab_type": {
            "type": "string",
            "enum": ["web-security", "network-defense", "active-directory", "custom"],
            "description": "Type of lab environment"
        },
        "vm_count": {
            "type": "integer",
            "description": "Number of VMs to deploy",
            "minimum": 1,
            "maximum": 20
        },
        "vms": {
            "type": "array",
            "description": "Specific VM configurations",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "os_type": {"type": "string", "enum": ["ubuntu", "windows", "kali", "rocky"]},
                    "role": {"type": "string", "enum": ["attacker", "target", "server", "workstation"]},
                    "packages": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "vulnerabilities": {
            "type": "array",
            "description": "Vulnerabilities to inject after deployment",
            "items": {
                "type": "string",
                "enum": ["sqli", "xss", "weak_ssh", "weak_rdp", "smb_vuln", "privilege_escalation"]
            }
        },
        "auto_inject_vulnerabilities": {
            "type": "boolean",
            "description": "Automatically start Reaper mission after lab deployment",
            "default": True
        }
    },
    "required": ["lab_name", "platform", "lab_type"]
}

CREATE_REAPER_MISSION_PARAMS = {
    "type": "object",
    "properties": {
        "mission_name": {
            "type": "string",
            "description": "Name for the Reaper mission"
        },
        "lab_id": {
            "type": "string",
            "description": "Lab deployment ID to target"
        },
        "mission_type": {
            "type": "string",
            "enum": ["web-security-lab", "network-defense-lab", "ad-lab", "custom"],
            "description": "Type of vulnerability injection mission"
        },
        "target_hosts": {
            "type": "array",
            "description": "Specific hosts to target (if not all lab VMs)",
            "items": {
                "type": "object",
                "properties": {
                    "host_id": {"type": "string"},
                    "os": {"type": "string", "enum": ["linux", "windows", "macos"]},
                    "ip_address": {"type": "string"}
                },
                "required": ["host_id", "os"]
            }
        },
        "vulnerability_categories": {
            "type": "array",
            "description": "Categories of vulnerabilities to inject",
            "items": {
                "type": "string",
                "enum": ["web", "network", "system", "authentication", "privilege_escalation"]
            }
        }
    },
    "required": ["mission_name", "lab_id", "mission_type"]
}

GET_STATUS_PARAMS = {
    "type": "object",
    "properties": {
        "resource_type": {
            "type": "string",
            "enum": ["system", "labs", "deployments", "missions", "vms", "hosts"],
            "description": "Type of resource to get status for"
        },
        "resource_id": {
            "type": "string",
            "description": "Specific resource ID (optional)"
        },
        "include_details": {
            "type": "boolean",
            "description": "Include detailed information",
            "default": False
        }
    },
    "required": ["resource_type"]
}

SEARCH_KNOWLEDGE_PARAMS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query for knowledge base"
        },
        "search_type": {
            "type": "string",
            "enum": ["general", "error", "documentation", "past_issues"],
            "description": "Type of search to perform"
        },
        "top_k": {
            "type": "integer",
            "description": "Number of results to return",
            "default": 5
        }
    },
    "required": ["query"]
}

LIST_RESOURCES_PARAMS = {
    "type": "object",
    "properties": {
        "resource_type": {
            "type": "string",
            "enum": ["labs", "deployments", "missions", "templates", "platforms"],
            "description": "Type of resources to list"
        },
        "status_filter": {
            "type": "string",
            "enum": ["all", "running", "pending", "completed", "failed"],
            "description": "Filter by status"
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results",
            "default": 10
        }
    },
    "required": ["resource_type"]
}

STOP_RESOURCE_PARAMS = {
    "type": "object",
    "properties": {
        "resource_type": {
            "type": "string",
            "enum": ["lab", "deployment", "mission", "vm"],
            "description": "Type of resource to stop"
        },
        "resource_id": {
            "type": "string",
            "description": "ID of the resource to stop"
        },
        "force": {
            "type": "boolean",
            "description": "Force stop without graceful shutdown",
            "default": False
        }
    },
    "required": ["resource_type", "resource_id"]
}

ASK_CLARIFICATION_PARAMS = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "Question to ask the operator"
        },
        "options": {
            "type": "array",
            "description": "Available options for the operator to choose from",
            "items": {"type": "string"}
        },
        "context": {
            "type": "string",
            "description": "Context for why this clarification is needed"
        }
    },
    "required": ["question"]
}

CONFIRM_ACTION_PARAMS = {
    "type": "object",
    "properties": {
        "action_type": {
            "type": "string",
            "description": "Type of action to confirm"
        },
        "action_summary": {
            "type": "string",
            "description": "Human-readable summary of the action"
        },
        "details": {
            "type": "object",
            "description": "Detailed parameters of the action"
        },
        "warnings": {
            "type": "array",
            "description": "Any warnings about the action",
            "items": {"type": "string"}
        }
    },
    "required": ["action_type", "action_summary", "details"]
}

DEPLOY_VM_PARAMS = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Name for the VM instance"
        },
        "platform": {
            "type": "string",
            "enum": ["aws", "proxmox", "azure", "esxi"],
            "description": "Cloud platform to deploy to"
        },
        "region": {
            "type": "string",
            "description": "AWS region (e.g., 'us-east-1', 'us-west-2'). Only for AWS."
        },
        "os_type": {
            "type": "string",
            "enum": ["ubuntu", "windows"],
            "description": "Operating system",
            "default": "ubuntu"
        },
        "instance_type": {
            "type": "string",
            "description": "Instance size (e.g., 't2.nano', 't2.micro', 't2.small' for AWS)"
        },
        "disk_size_gb": {
            "type": "integer",
            "description": "Disk size in GB",
            "default": 8
        }
    },
    "required": ["name", "platform"]
}

SEND_EMAIL_PARAMS = {
    "type": "object",
    "properties": {
        "to": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of recipient email addresses"
        },
        "subject": {
            "type": "string",
            "description": "Email subject line"
        },
        "body": {
            "type": "string",
            "description": "Email body content (plain text)"
        },
        "from_address": {
            "type": "string",
            "description": "Sender email address (defaults to overseer@xisx.org)"
        },
        "cc": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional CC recipients"
        },
        "html_body": {
            "type": "string",
            "description": "Optional HTML version of the email body"
        }
    },
    "required": ["to", "subject", "body"]
}

TERMINATE_VM_PARAMS = {
    "type": "object",
    "properties": {
        "platform": {
            "type": "string",
            "enum": ["aws", "proxmox", "azure", "esxi"],
            "description": "Cloud platform where the VM is running"
        },
        "instance_id": {
            "type": "string",
            "description": "Instance ID to terminate (e.g., AWS instance ID like 'i-1234567890abcdef0')"
        },
        "instance_name": {
            "type": "string",
            "description": "Instance name to terminate (alternative to instance_id)"
        },
        "region": {
            "type": "string",
            "description": "AWS region where the instance is located"
        }
    },
    "required": ["platform"]
}

GET_PLATFORM_STATUS_PARAMS = {
    "type": "object",
    "properties": {
        "platform": {
            "type": "string",
            "enum": ["aws", "proxmox", "azure", "esxi", "all"],
            "description": "Platform to check status for (use 'all' for all platforms)"
        },
        "region": {
            "type": "string",
            "description": "AWS region to check (e.g., 'us-east-1', 'us-west-2'). Leave empty for all regions."
        },
        "instance_id": {
            "type": "string",
            "description": "Specific instance/VM ID to check status for"
        },
        "show_all": {
            "type": "boolean",
            "description": "Show all instances including stopped ones",
            "default": True
        }
    },
    "required": ["platform"]
}


# ═══════════════════════════════════════════════════
# Tool Definitions
# ═══════════════════════════════════════════════════

OVERSEER_TOOLS: List[ToolDefinition] = [
    # Lab Deployment Tools
    ToolDefinition(
        name="deploy_lab",
        description=(
            "Deploy a new lab environment with VMs and networking. "
            "Use this when the operator wants to create a training lab, "
            "cyber range, or test environment. Can optionally auto-inject "
            "vulnerabilities via Reaper after deployment."
        ),
        parameters=DEPLOY_LAB_PARAMS,
        requires_confirmation=True,
        category="deployment"
    ),
    
    # Reaper Mission Tools
    ToolDefinition(
        name="create_reaper_mission",
        description=(
            "Create a Reaper vulnerability injection mission for an existing lab. "
            "Use this to inject security vulnerabilities into VMs for training purposes. "
            "The mission will discover services and inject appropriate vulnerabilities."
        ),
        parameters=CREATE_REAPER_MISSION_PARAMS,
        requires_confirmation=True,
        category="reaper"
    ),
    
    # Status and Query Tools
    ToolDefinition(
        name="get_status",
        description=(
            "Get the status of system resources, labs, deployments, missions, VMs, or hosts. "
            "Use this to check on running operations, system health, or resource state."
        ),
        parameters=GET_STATUS_PARAMS,
        requires_confirmation=False,
        category="query"
    ),
    
    ToolDefinition(
        name="list_resources",
        description=(
            "List available resources like labs, deployments, missions, templates, or platforms. "
            "Use this to show the operator what's available or currently running."
        ),
        parameters=LIST_RESOURCES_PARAMS,
        requires_confirmation=False,
        category="query"
    ),
    
    # Knowledge and Search Tools
    ToolDefinition(
        name="search_knowledge",
        description=(
            "Search the knowledge base for documentation, past issues, error solutions, "
            "or general information. Use this when you need context or the operator "
            "asks about previous events or documentation."
        ),
        parameters=SEARCH_KNOWLEDGE_PARAMS,
        requires_confirmation=False,
        category="search"
    ),
    
    # Control Tools
    ToolDefinition(
        name="stop_resource",
        description=(
            "Stop or cancel a running lab, deployment, mission, or VM. "
            "Use this when the operator wants to stop an operation or resource."
        ),
        parameters=STOP_RESOURCE_PARAMS,
        requires_confirmation=True,
        category="control"
    ),
    
    # Conversation Flow Tools
    ToolDefinition(
        name="ask_clarification",
        description=(
            "Ask the operator for clarification or additional information. "
            "Use this when you need more details to complete a request, "
            "such as which platform to use or specific configuration options."
        ),
        parameters=ASK_CLARIFICATION_PARAMS,
        requires_confirmation=False,
        category="conversation"
    ),
    
    ToolDefinition(
        name="confirm_action",
        description=(
            "ONLY use this for generic confirmations when no specific tool exists. "
            "Do NOT use for VM operations - use deploy_vm or terminate_vm instead. "
            "Do NOT use for Reaper missions - use create_reaper_mission instead. "
            "This is only for unusual actions not covered by other tools."
        ),
        parameters=CONFIRM_ACTION_PARAMS,
        requires_confirmation=False,
        category="conversation"
    ),
    
    # Single VM Deployment Tool
    ToolDefinition(
        name="deploy_vm",
        description=(
            "Deploy a single VM instance to a cloud platform. "
            "Use this for simple VM deployments like 'deploy a nano to AWS' or "
            "'create an Ubuntu VM on Proxmox'. Supports AWS (t2.nano, t2.micro, etc.), "
            "Proxmox, Azure, and ESXi."
        ),
        parameters=DEPLOY_VM_PARAMS,
        requires_confirmation=True,
        category="deployment"
    ),
    
    # Terminate/Destroy VM Tool
    ToolDefinition(
        name="terminate_vm",
        description=(
            "ALWAYS use this tool when asked to terminate, destroy, delete, or remove a VM. "
            "Do NOT use confirm_action for VM terminations - use this tool instead. "
            "This permanently deletes the instance. Requires platform and either instance_id or instance_name."
        ),
        parameters=TERMINATE_VM_PARAMS,
        requires_confirmation=True,
        category="control"
    ),
    
    # Send Email Tool
    ToolDefinition(
        name="send_email",
        description=(
            "Send an email notification or status update. Use this when the operator asks to "
            "send an email, notify someone, or send status updates. Emails are sent from "
            "the Glassdome mail server (xisx.org domain)."
        ),
        parameters=SEND_EMAIL_PARAMS,
        requires_confirmation=True,
        category="communication"
    ),
    
    # Platform Status Tool
    ToolDefinition(
        name="get_platform_status",
        description=(
            "Check the status of cloud platforms and their instances/VMs. "
            "Use this when the operator asks about deployment status, running instances, "
            "or wants to see what's currently deployed on AWS, Proxmox, Azure, or ESXi. "
            "Can check specific regions or all regions at once."
        ),
        parameters=GET_PLATFORM_STATUS_PARAMS,
        requires_confirmation=False,
        category="query"
    ),
]


def get_tools_by_category(category: str) -> List[ToolDefinition]:
    """Get tools filtered by category"""
    return [t for t in OVERSEER_TOOLS if t.category == category]


def get_tool_by_name(name: str) -> Optional[ToolDefinition]:
    """Get a specific tool by name"""
    for tool in OVERSEER_TOOLS:
        if tool.name == name:
            return tool
    return None


def get_tools_for_llm() -> List[Dict[str, Any]]:
    """
    Get tools in format suitable for LLM service
    
    Returns:
        List of tool dictionaries with name, description, parameters
    """
    from glassdome.chat.llm_service import Tool
    
    return [
        Tool(
            name=t.name,
            description=t.description,
            parameters=t.parameters
        )
        for t in OVERSEER_TOOLS
    ]


# ═══════════════════════════════════════════════════
# Lab Templates (Pre-configured lab types)
# ═══════════════════════════════════════════════════

LAB_TEMPLATES = {
    "web-security": {
        "name": "Web Security Training Lab",
        "description": "Lab for practicing web application security testing",
        "vms": [
            {"name": "attacker", "os_type": "kali", "role": "attacker", "packages": ["metasploit", "burpsuite"]},
            {"name": "web-server-1", "os_type": "ubuntu", "role": "target", "packages": ["apache2", "php", "mysql"]},
            {"name": "web-server-2", "os_type": "ubuntu", "role": "target", "packages": ["nginx", "nodejs"]},
        ],
        "vulnerabilities": ["sqli", "xss"],
        "networks": [
            {"name": "attack-net", "cidr": "192.168.100.0/24"},
            {"name": "dmz", "cidr": "10.0.1.0/24"}
        ]
    },
    "network-defense": {
        "name": "Network Defense Training Lab",
        "description": "Lab for practicing network security and defense",
        "vms": [
            {"name": "console", "os_type": "kali", "role": "attacker"},
            {"name": "router", "os_type": "ubuntu", "role": "server", "packages": ["iptables"]},
            {"name": "internal-server", "os_type": "ubuntu", "role": "target"},
            {"name": "workstation", "os_type": "ubuntu", "role": "workstation"},
        ],
        "vulnerabilities": ["weak_ssh", "smb_vuln", "privilege_escalation"],
        "networks": [
            {"name": "attack-net", "cidr": "192.168.100.0/24"},
            {"name": "internal", "cidr": "10.0.2.0/24"}
        ]
    },
    "active-directory": {
        "name": "Active Directory Security Lab",
        "description": "Lab for practicing Windows/AD security testing",
        "vms": [
            {"name": "attacker", "os_type": "kali", "role": "attacker"},
            {"name": "dc01", "os_type": "windows", "role": "server"},
            {"name": "workstation-1", "os_type": "windows", "role": "workstation"},
            {"name": "workstation-2", "os_type": "windows", "role": "workstation"},
        ],
        "vulnerabilities": ["weak_rdp", "privilege_escalation"],
        "networks": [
            {"name": "attack-net", "cidr": "192.168.100.0/24"},
            {"name": "corp-net", "cidr": "10.0.3.0/24"}
        ]
    }
}


def get_lab_template(template_name: str) -> Optional[Dict[str, Any]]:
    """Get a lab template by name"""
    return LAB_TEMPLATES.get(template_name)


def list_lab_templates() -> List[Dict[str, str]]:
    """List available lab templates"""
    return [
        {"name": name, "description": template["description"]}
        for name, template in LAB_TEMPLATES.items()
    ]

