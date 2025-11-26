#!/usr/bin/env python3
"""
WhiteKnight Agent - Automated Vulnerability Validation

This agent runs inside a container and validates that exploits
have been successfully deployed by attempting to exploit them.
"""

import argparse
import json
import sys
import os
import subprocess
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("whiteknight")


class ValidationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ValidationResult:
    status: ValidationStatus
    exploit_type: str
    target_ip: str
    evidence: str = ""
    details: Dict[str, Any] = None
    
    def to_dict(self):
        return {
            "status": self.status.value,
            "exploit_type": self.exploit_type,
            "target_ip": self.target_ip,
            "evidence": self.evidence,
            "details": self.details or {}
        }


class WhiteKnightAgent:
    """Main agent that coordinates vulnerability validation"""
    
    def __init__(self):
        self.validators = {
            "CREDENTIAL": self.validate_credentials,
            "WEB": self.validate_web,
            "NETWORK": self.validate_network,
            "PRIVESC": self.validate_privesc,
            "MISCONFIG": self.validate_misconfig,
        }
    
    async def validate(self, target_ip: str, exploit_config: Dict[str, Any]) -> ValidationResult:
        """
        Main validation entry point
        
        Args:
            target_ip: IP address of target VM
            exploit_config: Exploit configuration from Reaper
                - exploit_type: CREDENTIAL, WEB, NETWORK, etc.
                - name: Exploit name
                - tags: List of tags for specific handling
                - verify_command: Optional custom verification command
        """
        exploit_type = exploit_config.get("exploit_type", "UNKNOWN")
        name = exploit_config.get("name", "Unknown Exploit")
        
        logger.info(f"🎯 Validating: {name} ({exploit_type}) on {target_ip}")
        
        # Check if custom verify command provided
        if exploit_config.get("verify_command"):
            return await self.run_custom_verify(target_ip, exploit_config)
        
        # Use type-specific validator
        validator = self.validators.get(exploit_type)
        if validator:
            return await validator(target_ip, exploit_config)
        
        # Fallback to generic validation
        return await self.validate_generic(target_ip, exploit_config)
    
    async def run_custom_verify(self, target_ip: str, config: Dict) -> ValidationResult:
        """Run a custom verification command"""
        cmd = config["verify_command"].replace("{target}", target_ip)
        logger.info(f"Running custom verify: {cmd}")
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60
            )
            success = result.returncode == 0
            return ValidationResult(
                status=ValidationStatus.SUCCESS if success else ValidationStatus.FAILED,
                exploit_type=config.get("exploit_type", "CUSTOM"),
                target_ip=target_ip,
                evidence=result.stdout[:1000],
                details={"stderr": result.stderr[:500], "exit_code": result.returncode}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type=config.get("exploit_type", "CUSTOM"),
                target_ip=target_ip,
                evidence="Command timed out"
            )
    
    # =========================================================================
    # CREDENTIAL VALIDATORS
    # =========================================================================
    
    async def validate_credentials(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate credential-based exploits (SSH, FTP, etc.)"""
        tags = config.get("tags", [])
        
        if "ssh" in tags:
            return await self.validate_ssh_credentials(target_ip, config)
        elif "ftp" in tags:
            return await self.validate_ftp_credentials(target_ip, config)
        
        # Default SSH check
        return await self.validate_ssh_credentials(target_ip, config)
    
    async def validate_ssh_credentials(self, target_ip: str, config: Dict) -> ValidationResult:
        """Test weak SSH credentials using sshpass"""
        # Default weak creds to test
        username = config.get("username", "user")
        password = config.get("password", "password123")
        
        logger.info(f"Testing SSH credentials: {username}:{password}")
        
        cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {username}@{target_ip} 'echo SUCCESS; id; hostname'"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            
            if "SUCCESS" in result.stdout:
                logger.info(f"✅ SSH login successful!")
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    exploit_type="CREDENTIAL",
                    target_ip=target_ip,
                    evidence=f"SSH login successful with {username}:{password}\n{result.stdout}",
                    details={"username": username, "method": "ssh"}
                )
            else:
                logger.warning(f"❌ SSH login failed")
                return ValidationResult(
                    status=ValidationStatus.FAILED,
                    exploit_type="CREDENTIAL",
                    target_ip=target_ip,
                    evidence=f"SSH login failed\n{result.stderr}",
                    details={"username": username}
                )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="CREDENTIAL",
                target_ip=target_ip,
                evidence="SSH connection timed out"
            )
    
    async def validate_ftp_credentials(self, target_ip: str, config: Dict) -> ValidationResult:
        """Test weak FTP credentials"""
        username = config.get("username", "anonymous")
        password = config.get("password", "anonymous@")
        
        cmd = f"curl -s --connect-timeout 10 ftp://{username}:{password}@{target_ip}/"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            success = result.returncode == 0 and len(result.stdout) > 0
            return ValidationResult(
                status=ValidationStatus.SUCCESS if success else ValidationStatus.FAILED,
                exploit_type="CREDENTIAL",
                target_ip=target_ip,
                evidence=result.stdout[:500] if success else result.stderr[:500]
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="CREDENTIAL",
                target_ip=target_ip,
                evidence="FTP connection timed out"
            )
    
    # =========================================================================
    # WEB VALIDATORS
    # =========================================================================
    
    async def validate_web(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate web-based exploits"""
        tags = config.get("tags", [])
        
        if "sqli" in tags or "injection" in tags:
            return await self.validate_sqli(target_ip, config)
        elif "xss" in tags:
            return await self.validate_xss(target_ip, config)
        elif "dvwa" in tags or "training" in tags:
            return await self.validate_dvwa(target_ip, config)
        
        # Default: check if web service is running with vulnerabilities
        return await self.validate_web_generic(target_ip, config)
    
    async def validate_sqli(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate SQL injection using sqlmap"""
        port = config.get("port", 80)
        path = config.get("path", "/")
        
        logger.info(f"Testing SQL injection on http://{target_ip}:{port}{path}")
        
        # Quick sqlmap scan
        cmd = f"sqlmap -u 'http://{target_ip}:{port}{path}?id=1' --batch --level=1 --risk=1 --timeout=10 --retries=1 2>&1 | head -50"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120
            )
            
            # Check for successful injection indicators
            success_indicators = [
                "is vulnerable",
                "injectable",
                "SQL injection",
                "payload:"
            ]
            
            is_vulnerable = any(ind in result.stdout for ind in success_indicators)
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if is_vulnerable else ValidationStatus.FAILED,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence=result.stdout[:1000],
                details={"method": "sqlmap", "path": path}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence="SQLMap scan timed out"
            )
    
    async def validate_dvwa(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate DVWA is installed and accessible"""
        port = config.get("port", 80)
        
        logger.info(f"Checking DVWA on http://{target_ip}:{port}")
        
        cmd = f"curl -s --connect-timeout 10 http://{target_ip}:{port}/DVWA/ 2>&1 | head -20"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            
            # Check for DVWA indicators
            dvwa_indicators = ["DVWA", "Damn Vulnerable", "dvwa", "login.php"]
            is_dvwa = any(ind in result.stdout for ind in dvwa_indicators)
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if is_dvwa else ValidationStatus.FAILED,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence=result.stdout[:500],
                details={"app": "DVWA", "port": port}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence="DVWA check timed out"
            )
    
    async def validate_xss(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate XSS vulnerability"""
        port = config.get("port", 80)
        path = config.get("path", "/")
        
        # Simple XSS payload test
        payload = "<script>alert('XSS')</script>"
        cmd = f"curl -s --connect-timeout 10 'http://{target_ip}:{port}{path}?q={payload}' 2>&1"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            
            # Check if payload is reflected
            is_reflected = payload in result.stdout or "alert" in result.stdout
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if is_reflected else ValidationStatus.FAILED,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence=result.stdout[:500] if is_reflected else "Payload not reflected",
                details={"method": "reflected_xss"}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence="XSS test timed out"
            )
    
    async def validate_web_generic(self, target_ip: str, config: Dict) -> ValidationResult:
        """Generic web vulnerability check using nikto"""
        port = config.get("port", 80)
        
        logger.info(f"Running nikto scan on http://{target_ip}:{port}")
        
        cmd = f"nikto -h http://{target_ip}:{port} -maxtime 60s 2>&1 | head -30"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120
            )
            
            # Check for vulnerability indicators
            vuln_count = result.stdout.count("+ ")
            has_vulns = vuln_count > 2  # More than just headers
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if has_vulns else ValidationStatus.FAILED,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence=result.stdout[:1000],
                details={"method": "nikto", "findings": vuln_count}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence="Nikto scan timed out"
            )
    
    # =========================================================================
    # NETWORK VALIDATORS
    # =========================================================================
    
    async def validate_network(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate network-based exploits"""
        tags = config.get("tags", [])
        
        if "smb" in tags:
            return await self.validate_smb(target_ip, config)
        
        # Default port scan
        return await self.validate_open_ports(target_ip, config)
    
    async def validate_smb(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate SMB anonymous access"""
        logger.info(f"Testing SMB anonymous access on {target_ip}")
        
        cmd = f"smbclient -L //{target_ip} -N 2>&1"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            
            # Check for successful share listing
            has_shares = "Disk" in result.stdout or "Sharename" in result.stdout
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if has_shares else ValidationStatus.FAILED,
                exploit_type="NETWORK",
                target_ip=target_ip,
                evidence=result.stdout[:500],
                details={"method": "smb_anonymous"}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="NETWORK",
                target_ip=target_ip,
                evidence="SMB check timed out"
            )
    
    async def validate_open_ports(self, target_ip: str, config: Dict) -> ValidationResult:
        """Quick port scan to verify services"""
        ports = config.get("ports", "22,80,443,445,3306")
        
        cmd = f"nmap -p {ports} --open -T4 {target_ip} 2>&1"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60
            )
            
            has_open = "open" in result.stdout
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if has_open else ValidationStatus.FAILED,
                exploit_type="NETWORK",
                target_ip=target_ip,
                evidence=result.stdout[:500],
                details={"method": "nmap"}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="NETWORK",
                target_ip=target_ip,
                evidence="Port scan timed out"
            )
    
    # =========================================================================
    # PRIVILEGE ESCALATION VALIDATORS
    # =========================================================================
    
    async def validate_privesc(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate privilege escalation vulnerabilities"""
        tags = config.get("tags", [])
        
        if "sudo" in tags:
            return await self.validate_sudo_privesc(target_ip, config)
        
        return await self.validate_privesc_generic(target_ip, config)
    
    async def validate_sudo_privesc(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate sudo NOPASSWD misconfiguration"""
        username = config.get("username", "user")
        password = config.get("password", "password123")
        
        # SSH in and check sudo -l
        cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{target_ip} 'sudo -l 2>&1'"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            
            # Check for NOPASSWD
            has_nopasswd = "NOPASSWD" in result.stdout
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if has_nopasswd else ValidationStatus.FAILED,
                exploit_type="PRIVESC",
                target_ip=target_ip,
                evidence=result.stdout[:500],
                details={"method": "sudo_nopasswd", "username": username}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="PRIVESC",
                target_ip=target_ip,
                evidence="Sudo check timed out"
            )
    
    async def validate_privesc_generic(self, target_ip: str, config: Dict) -> ValidationResult:
        """Generic privesc check"""
        return ValidationResult(
            status=ValidationStatus.FAILED,
            exploit_type="PRIVESC",
            target_ip=target_ip,
            evidence="No specific privesc validator for this exploit"
        )
    
    # =========================================================================
    # MISCONFIGURATION VALIDATORS
    # =========================================================================
    
    async def validate_misconfig(self, target_ip: str, config: Dict) -> ValidationResult:
        """Validate misconfiguration exploits"""
        return await self.validate_generic(target_ip, config)
    
    async def validate_generic(self, target_ip: str, config: Dict) -> ValidationResult:
        """Generic validation - just check connectivity"""
        cmd = f"ping -c 1 -W 5 {target_ip}"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if result.returncode == 0 else ValidationStatus.FAILED,
                exploit_type=config.get("exploit_type", "UNKNOWN"),
                target_ip=target_ip,
                evidence="Target is reachable" if result.returncode == 0 else "Target unreachable"
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type=config.get("exploit_type", "UNKNOWN"),
                target_ip=target_ip,
                evidence="Ping timed out"
            )


# =============================================================================
# METASPLOIT INTEGRATION
# =============================================================================

class MetasploitRunner:
    """Run Metasploit modules for validation"""
    
    # Map exploit types to MSF modules
    MSF_MODULES = {
        "ssh_login": "auxiliary/scanner/ssh/ssh_login",
        "smb_shares": "auxiliary/scanner/smb/smb_enumshares",
        "smb_version": "auxiliary/scanner/smb/smb_version",
        "http_version": "auxiliary/scanner/http/http_version",
        "ftp_login": "auxiliary/scanner/ftp/ftp_login",
    }
    
    async def run_module(self, module_name: str, target_ip: str, options: Dict = None) -> Dict:
        """Run an MSF module and return results"""
        module = self.MSF_MODULES.get(module_name, module_name)
        options = options or {}
        
        # Build resource script
        rc_content = f"use {module}\n"
        rc_content += f"set RHOSTS {target_ip}\n"
        for key, value in options.items():
            rc_content += f"set {key} {value}\n"
        rc_content += "run\nexit\n"
        
        # Write temp RC file
        rc_file = "/tmp/msf_validate.rc"
        with open(rc_file, "w") as f:
            f.write(rc_content)
        
        logger.info(f"Running MSF module: {module}")
        
        cmd = f"msfconsole -q -r {rc_file} 2>&1"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "module": module
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "MSF module timed out",
                "module": module
            }


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="WhiteKnight Vulnerability Validator")
    parser.add_argument("--target", "-t", required=True, help="Target IP address")
    parser.add_argument("--config", "-c", help="JSON config file or inline JSON")
    parser.add_argument("--type", help="Exploit type (CREDENTIAL, WEB, NETWORK, PRIVESC)")
    parser.add_argument("--name", help="Exploit name")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--username", default="user", help="Username for credential tests")
    parser.add_argument("--password", default="password123", help="Password for credential tests")
    parser.add_argument("--output", "-o", choices=["json", "text"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    # Build config
    if args.config:
        if os.path.exists(args.config):
            with open(args.config) as f:
                config = json.load(f)
        else:
            config = json.loads(args.config)
    else:
        config = {
            "exploit_type": args.type or "CREDENTIAL",
            "name": args.name or "Manual Test",
            "tags": args.tags.split(",") if args.tags else [],
            "username": args.username,
            "password": args.password,
        }
    
    # Run validation
    agent = WhiteKnightAgent()
    result = asyncio.run(agent.validate(args.target, config))
    
    # Output
    if args.output == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status_icon = "✅" if result.status == ValidationStatus.SUCCESS else "❌"
        print(f"\n{status_icon} Validation Result: {result.status.value.upper()}")
        print(f"   Target: {result.target_ip}")
        print(f"   Type: {result.exploit_type}")
        print(f"   Evidence: {result.evidence[:200]}...")
    
    # Exit code
    sys.exit(0 if result.status == ValidationStatus.SUCCESS else 1)


if __name__ == "__main__":
    main()

