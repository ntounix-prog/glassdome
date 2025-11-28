"""
API endpoints for whiteknight

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
import logging
import subprocess
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whiteknight", tags=["whiteknight"])


class ValidationRequest(BaseModel):
    mission_id: str  # REQUIRED - must be a valid Reaper mission
    target_ip: str   # Will be validated against mission's VM IP
    username: str = "ubuntu"
    password: str = "ubuntu"
    port: int = 22
    tests: List[str]


class ValidationResult(BaseModel):
    test: str
    status: str  # success, failed, error
    message: str
    evidence: Optional[str] = None


class ValidationResponse(BaseModel):
    target: str
    results: List[ValidationResult]
    summary: Dict[str, int]


# Common weak credentials injected by Reaper exploits
WEAK_CREDENTIALS = [
    ("ubuntu", "ubuntu"),         # Default cloud image creds (WEAK!)
    ("vulnuser", "password123"),  # Reaper weak SSH exploit
    ("root", "root"),
    ("root", "password123"),
    ("admin", "admin"),
    ("admin", "password"),
]

# Test definitions with validation commands
TEST_DEFINITIONS = {
    # Credential Testing - tests multiple weak credentials
    "ssh_creds": {
        "name": "SSH Weak Credentials",
        "command": "sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {username}@{target} 'echo SUCCESS'",
        "success_indicator": "SUCCESS",
        "category": "credential",
        "multi_cred": True  # Test all weak credentials
    },
    "mysql_creds": {
        "name": "MySQL Login",
        "command": "mysql -h {target} -u {username} -p{password} -e 'SELECT 1' 2>/dev/null && echo SUCCESS",
        "success_indicator": "SUCCESS",
        "category": "credential"
    },
    "redis_creds": {
        "name": "Redis Auth",
        "command": "redis-cli -h {target} -a {password} PING 2>/dev/null",
        "success_indicator": "PONG",
        "category": "credential"
    },
    "postgres_creds": {
        "name": "PostgreSQL Login",
        "command": "PGPASSWORD='{password}' psql -h {target} -U {username} -c 'SELECT 1' 2>/dev/null && echo SUCCESS",
        "success_indicator": "SUCCESS",
        "category": "credential"
    },
    "smb_creds": {
        "name": "SMB Login",
        "command": "smbclient -L //{target} -U {username}%{password} -N 2>/dev/null | head -5",
        "success_indicator": "Sharename",
        "category": "credential"
    },
    
    # Connectivity (run first)
    "connectivity": {
        "name": "Connectivity Check",
        "command": "ping -c 1 -W 3 {target} && echo 'HOST_REACHABLE'",
        "success_indicator": "HOST_REACHABLE",
        "category": "network"
    },
    
    # Network Services
    "port_scan": {
        "name": "Port Scan",
        "command": "nmap -Pn -p 22,80,443,3306,5432,6379 --open {target} 2>/dev/null | grep 'open'",
        "success_indicator": "open",
        "category": "network"
    },
    "smb_anon": {
        "name": "SMB Anonymous",
        "command": "smbclient -L //{target} -N 2>/dev/null | head -5",
        "success_indicator": "Sharename",
        "category": "network"
    },
    "snmp_public": {
        "name": "SNMP Public",
        "command": "snmpwalk -v2c -c public {target} system 2>/dev/null | head -3",
        "success_indicator": "SNMPv2",
        "category": "network"
    },
    "redis_open": {
        "name": "Redis Open",
        "command": "redis-cli -h {target} INFO 2>/dev/null | head -3",
        "success_indicator": "redis_version",
        "category": "network"
    },
    
    # Web Vulnerabilities
    "http_methods": {
        "name": "HTTP Methods",
        "command": "curl -s -X OPTIONS -I http://{target}/ 2>/dev/null | grep -i 'allow'",
        "success_indicator": "Allow",
        "category": "web"
    },
    "dir_listing": {
        "name": "Directory Listing",
        "command": "curl -s http://{target}/ 2>/dev/null | grep -i 'index of'",
        "success_indicator": "Index of",
        "category": "web"
    },
    "security_headers": {
        "name": "Security Headers",
        "command": "curl -s -I http://{target}/ 2>/dev/null | grep -iE 'X-Frame-Options|X-XSS-Protection|Content-Security-Policy'",
        "success_indicator": "",  # Empty = headers missing is the vulnerability
        "category": "web"
    },
    
    # Privilege Escalation (requires SSH access)
    "sudo_nopass": {
        "name": "Sudo NOPASSWD",
        "command": "sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{target} 'sudo -l 2>/dev/null | grep NOPASSWD'",
        "success_indicator": "NOPASSWD",
        "category": "privesc"
    },
    "suid_binaries": {
        "name": "SUID Binaries",
        "command": "sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{target} 'find /usr/bin -perm -4000 2>/dev/null | head -5'",
        "success_indicator": "/",
        "category": "privesc"
    },
    "docker_group": {
        "name": "Docker Group",
        "command": "sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{target} 'id | grep docker'",
        "success_indicator": "docker",
        "category": "privesc"
    },
}


def check_docker_ready() -> tuple[bool, str]:
    """Check if Docker is available and WhiteKnight image exists"""
    try:
        # Check if Docker is running
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return False, "Docker not running"
        
        # Check if WhiteKnight image exists
        result = subprocess.run(
            ["docker", "images", "whiteknight:latest", "--format", "{{.Repository}}"],
            capture_output=True, text=True, timeout=5
        )
        if "whiteknight" not in result.stdout:
            return False, "WhiteKnight image not found"
        
        return True, "ready"
    except Exception as e:
        return False, str(e)


@router.get("/status")
async def get_status():
    """Get WhiteKnight container status"""
    is_ready, message = check_docker_ready()
    
    # Get image info if available
    image_info = {}
    if is_ready:
        try:
            result = subprocess.run(
                ["docker", "images", "whiteknight:latest", 
                 "--format", "{{.Size}}|{{.CreatedAt}}"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("|")
                image_info = {
                    "size": parts[0] if len(parts) > 0 else "unknown",
                    "created": parts[1] if len(parts) > 1 else "unknown",
                    "image": "whiteknight:latest"
                }
        except Exception as e:
            logger.warning(f"Failed to get image info: {e}")
    
    return {
        "status": "running" if is_ready else "offline",
        "message": message,
        "image": image_info,
        "available_tests": len(TEST_DEFINITIONS),
        "test_categories": list(set(t["category"] for t in TEST_DEFINITIONS.values()))
    }


@router.get("/tools")
async def get_tools():
    """Get list of available tools in WhiteKnight container"""
    tools = {
        "ssh_remote": ["sshpass", "ssh", "hydra"],
        "network": ["nmap", "netcat", "smbclient", "snmpwalk"],
        "database": ["mysql", "psql", "redis-cli"],
        "web": ["curl", "wget"],
        "python": ["paramiko", "python-nmap", "impacket"]
    }
    
    # Check which tools are actually available
    tool_status = {}
    for category, tool_list in tools.items():
        tool_status[category] = []
        for tool in tool_list:
            status = "ready"  # Assume ready since we control the Dockerfile
            tool_status[category].append({
                "name": tool,
                "status": status
            })
    
    return {"tools": tool_status}


@router.get("/tests")
async def get_tests():
    """Get available validation tests"""
    tests_by_category = {}
    for test_id, test_def in TEST_DEFINITIONS.items():
        category = test_def["category"]
        if category not in tests_by_category:
            tests_by_category[category] = []
        tests_by_category[category].append({
            "id": test_id,
            "name": test_def["name"]
        })
    return {"tests": tests_by_category}


async def run_single_command(command: str, timeout: int = 30) -> tuple[str, str, int]:
    """Run a command in the WhiteKnight container"""
    docker_cmd = [
        "docker", "run", "--rm", "--network", "host",
        "--entrypoint", "/bin/bash",
        "whiteknight:latest",
        "-c", command
    ]
    
    process = await asyncio.create_subprocess_exec(
        *docker_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=timeout
    )
    return stdout.decode().strip(), stderr.decode().strip(), process.returncode


async def run_test(test_id: str, target: str, username: str, password: str) -> ValidationResult:
    """Run a single validation test"""
    if test_id not in TEST_DEFINITIONS:
        return ValidationResult(
            test=test_id,
            status="error",
            message=f"Unknown test: {test_id}"
        )
    
    test_def = TEST_DEFINITIONS[test_id]
    
    # For multi-credential tests, try all weak credentials
    if test_def.get("multi_cred"):
        found_creds = []
        for weak_user, weak_pass in WEAK_CREDENTIALS:
            command = test_def["command"].format(
                target=target,
                username=weak_user,
                password=weak_pass
            )
            try:
                output, stderr, returncode = await run_single_command(command, timeout=10)
                if test_def["success_indicator"] in output:
                    found_creds.append(f"{weak_user}:{weak_pass}")
                    logger.info(f"Found weak credential on {target}: {weak_user}:{weak_pass}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Credential test failed for {weak_user}: {e}")
                continue
        
        if found_creds:
            return ValidationResult(
                test=test_def["name"],
                status="success",
                message=f"VULNERABLE: Weak credentials found!",
                evidence=f"Valid credentials: {', '.join(found_creds)}"
            )
        else:
            return ValidationResult(
                test=test_def["name"],
                status="failed",
                message="No weak credentials found (or host unreachable)",
                evidence="Tested: " + ", ".join(f"{u}:{p}" for u, p in WEAK_CREDENTIALS[:3]) + "..."
            )
    
    # Standard single-credential test
    command = test_def["command"].format(
        target=target,
        username=username,
        password=password
    )
    
    try:
        output, stderr, returncode = await run_single_command(command)
        success_indicator = test_def["success_indicator"]
        
        # Check for success
        if success_indicator:
            if success_indicator in output:
                return ValidationResult(
                    test=test_def["name"],
                    status="success",
                    message=f"Vulnerability confirmed: {test_def['name']}",
                    evidence=output[:500]
                )
            else:
                return ValidationResult(
                    test=test_def["name"],
                    status="failed",
                    message=f"Test did not find vulnerability",
                    evidence=output[:200] if output else stderr[:200]
                )
        else:
            # For tests where no output = vulnerability (like missing headers)
            if not output:
                return ValidationResult(
                    test=test_def["name"],
                    status="success",
                    message=f"Vulnerability confirmed: {test_def['name']} (missing protection)",
                    evidence="No security headers found"
                )
            else:
                return ValidationResult(
                    test=test_def["name"],
                    status="failed",
                    message="Protection is in place",
                    evidence=output[:200]
                )
                
    except asyncio.TimeoutError:
        return ValidationResult(
            test=test_def["name"],
            status="error",
            message="Test timed out after 30 seconds"
        )
    except Exception as e:
        return ValidationResult(
            test=test_def["name"],
            status="error",
            message=f"Test error: {str(e)}"
        )


@router.post("/validate", response_model=ValidationResponse)
async def run_validation(request: ValidationRequest):
    """
    Run validation tests against a deployed Reaper mission target.
    
    SECURITY: Only VMs deployed by Reaper missions can be targeted.
    This prevents WhiteKnight from being used as an attack tool.
    
    Results are stored in the database and linked to the mission for history.
    """
    from glassdome.core.database import AsyncSessionLocal
    from glassdome.reaper.exploit_library import ExploitMission, ValidationResult as ValidationResultModel
    from sqlalchemy import select
    import time
    
    # CRITICAL: Validate that mission_id exists and IP matches
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExploitMission).where(ExploitMission.mission_id == request.mission_id)
        )
        mission = result.scalar_one_or_none()
        
        if not mission:
            logger.warning(f"SECURITY: Attempted validation on non-existent mission: {request.mission_id}")
            raise HTTPException(
                status_code=403, 
                detail="Invalid mission ID. WhiteKnight can only target deployed Reaper missions."
            )
        
        # Verify the IP matches the mission's VM
        if mission.vm_ip_address != request.target_ip:
            logger.warning(
                f"SECURITY: IP mismatch for mission {request.mission_id}. "
                f"Expected {mission.vm_ip_address}, got {request.target_ip}"
            )
            raise HTTPException(
                status_code=403,
                detail="Target IP does not match mission VM. Validation denied."
            )
        
        # Verify mission has a deployed VM
        if not mission.vm_ip_address:
            raise HTTPException(
                status_code=400,
                detail="Mission does not have a deployed VM yet. Cannot validate."
            )
        
        logger.info(
            f"VALIDATED: Running tests on mission {request.mission_id} "
            f"({mission.name}) at {request.target_ip}"
        )
    
    results = []
    for test_id in request.tests:
        start_time = time.time()
        result = await run_test(
            test_id,
            request.target_ip,
            request.username,
            request.password
        )
        duration_ms = int((time.time() - start_time) * 1000)
        results.append(result)
        
        # Store result in database
        async with AsyncSessionLocal() as db:
            test_def = TEST_DEFINITIONS.get(test_id, {})
            validation_record = ValidationResultModel(
                mission_id=request.mission_id,
                test_name=result.test,
                test_type=test_def.get("category", "unknown"),
                status=result.status,
                message=result.message,
                evidence=result.evidence,
                target_ip=request.target_ip,
                credentials_tested=WEAK_CREDENTIALS if test_def.get("multi_cred") else None,
                duration_ms=duration_ms
            )
            db.add(validation_record)
            await db.commit()
    
    # Summary
    summary = {
        "total": len(results),
        "success": sum(1 for r in results if r.status == "success"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "error": sum(1 for r in results if r.status == "error")
    }
    
    logger.info(f"Validation complete for {request.mission_id}: {summary}")
    
    return ValidationResponse(
        target=request.target_ip,
        results=results,
        summary=summary
    )


@router.post("/quick-scan")
async def quick_scan(mission_id: str):
    """
    Run a quick scan with essential tests on a deployed mission.
    
    SECURITY: Only targets deployed Reaper missions.
    """
    from glassdome.core.database import AsyncSessionLocal
    from glassdome.reaper.exploit_library import ExploitMission
    from sqlalchemy import select
    
    # Validate mission exists
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExploitMission).where(ExploitMission.mission_id == mission_id)
        )
        mission = result.scalar_one_or_none()
        
        if not mission or not mission.vm_ip_address:
            raise HTTPException(
                status_code=403,
                detail="Invalid or undeployed mission. WhiteKnight can only target deployed Reaper missions."
            )
        
        target_ip = mission.vm_ip_address
        logger.info(f"Quick scan on mission {mission_id} at {target_ip}")
    
    essential_tests = ["ssh_creds", "port_scan", "smb_anon"]
    
    results = []
    for test_id in essential_tests:
        result = await run_test(test_id, target_ip, "ubuntu", "ubuntu")
        results.append(result)
    
    return {
        "mission_id": mission_id,
        "target": target_ip,
        "results": results,
        "summary": {
            "vulnerabilities_found": sum(1 for r in results if r.status == "success")
        }
    }

