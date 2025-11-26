"""
WhiteKnight Client - Interface for Glassdome/Reaper

This client manages the WhiteKnight container and provides
a clean interface for validating exploits.
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to WhiteKnight directory
WHITEKNIGHT_DIR = Path(__file__).parent.parent.parent / "whiteknight"


class ValidationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ValidationResult:
    """Result of a WhiteKnight validation"""
    status: ValidationStatus
    exploit_type: str
    target_ip: str
    evidence: str = ""
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "exploit_type": self.exploit_type,
            "target_ip": self.target_ip,
            "evidence": self.evidence,
            "details": self.details or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ValidationResult":
        return cls(
            status=ValidationStatus(data["status"]),
            exploit_type=data["exploit_type"],
            target_ip=data["target_ip"],
            evidence=data.get("evidence", ""),
            details=data.get("details", {})
        )


class WhiteKnightClient:
    """
    Client for running WhiteKnight validations.
    
    Can run in two modes:
    1. Docker mode - Runs WhiteKnight in a container (production)
    2. Local mode - Runs validation scripts directly (development)
    """
    
    CONTAINER_IMAGE = "whiteknight:latest"
    
    def __init__(self, use_docker: bool = True):
        self.use_docker = use_docker
        self._docker_available = None
    
    async def is_docker_available(self) -> bool:
        """Check if Docker is available"""
        if self._docker_available is None:
            try:
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    timeout=5
                )
                self._docker_available = result.returncode == 0
            except Exception:
                self._docker_available = False
        return self._docker_available
    
    async def is_image_built(self) -> bool:
        """Check if WhiteKnight image exists"""
        try:
            result = subprocess.run(
                ["docker", "images", "-q", self.CONTAINER_IMAGE],
                capture_output=True,
                text=True,
                timeout=10
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    async def build_image(self) -> bool:
        """Build the WhiteKnight Docker image"""
        logger.info("Building WhiteKnight Docker image...")
        
        try:
            result = subprocess.run(
                ["docker", "build", "-t", self.CONTAINER_IMAGE, str(WHITEKNIGHT_DIR)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for build
            )
            
            if result.returncode == 0:
                logger.info("WhiteKnight image built successfully")
                return True
            else:
                logger.error(f"Failed to build WhiteKnight image: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("WhiteKnight image build timed out")
            return False
        except Exception as e:
            logger.error(f"Error building WhiteKnight image: {e}")
            return False
    
    async def validate(
        self,
        target_ip: str,
        exploit_config: Dict[str, Any],
        timeout: int = 300
    ) -> ValidationResult:
        """
        Validate an exploit on a target.
        
        Args:
            target_ip: IP address of target VM
            exploit_config: Exploit configuration dict:
                - exploit_type: CREDENTIAL, WEB, NETWORK, PRIVESC
                - name: Exploit name
                - tags: List of tags
                - username/password: For credential tests
                - verify_command: Optional custom command
            timeout: Timeout in seconds
            
        Returns:
            ValidationResult with status and evidence
        """
        if self.use_docker and await self.is_docker_available():
            return await self._validate_docker(target_ip, exploit_config, timeout)
        else:
            return await self._validate_local(target_ip, exploit_config, timeout)
    
    async def _validate_docker(
        self,
        target_ip: str,
        exploit_config: Dict[str, Any],
        timeout: int
    ) -> ValidationResult:
        """Run validation in Docker container"""
        
        # Ensure image is built
        if not await self.is_image_built():
            if not await self.build_image():
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    exploit_type=exploit_config.get("exploit_type", "UNKNOWN"),
                    target_ip=target_ip,
                    evidence="Failed to build WhiteKnight image"
                )
        
        # Build docker command
        config_json = json.dumps(exploit_config)
        
        cmd = [
            "docker", "run", "--rm",
            "--network", "host",  # Use host network to reach VMs
            self.CONTAINER_IMAGE,
            "--target", target_ip,
            "--config", config_json,
            "--output", "json"
        ]
        
        logger.info(f"Running WhiteKnight validation for {target_ip}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Parse JSON output
            try:
                output = json.loads(result.stdout)
                return ValidationResult.from_dict(output)
            except json.JSONDecodeError:
                # Couldn't parse output
                return ValidationResult(
                    status=ValidationStatus.SUCCESS if result.returncode == 0 else ValidationStatus.FAILED,
                    exploit_type=exploit_config.get("exploit_type", "UNKNOWN"),
                    target_ip=target_ip,
                    evidence=result.stdout[:1000] if result.stdout else result.stderr[:1000]
                )
                
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type=exploit_config.get("exploit_type", "UNKNOWN"),
                target_ip=target_ip,
                evidence=f"Validation timed out after {timeout}s"
            )
        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                exploit_type=exploit_config.get("exploit_type", "UNKNOWN"),
                target_ip=target_ip,
                evidence=str(e)
            )
    
    async def _validate_local(
        self,
        target_ip: str,
        exploit_config: Dict[str, Any],
        timeout: int
    ) -> ValidationResult:
        """
        Run validation locally without Docker.
        Uses available system tools directly.
        """
        exploit_type = exploit_config.get("exploit_type", "UNKNOWN")
        tags = exploit_config.get("tags", [])
        
        logger.info(f"Running local validation for {target_ip} ({exploit_type})")
        
        # Quick local validators
        if exploit_type == "CREDENTIAL" or "ssh" in tags:
            return await self._local_ssh_check(target_ip, exploit_config, timeout)
        elif exploit_type == "NETWORK" or "smb" in tags:
            return await self._local_smb_check(target_ip, timeout)
        elif exploit_type == "WEB":
            return await self._local_web_check(target_ip, exploit_config, timeout)
        else:
            return await self._local_ping_check(target_ip, timeout)
    
    async def _local_ssh_check(
        self,
        target_ip: str,
        config: Dict,
        timeout: int
    ) -> ValidationResult:
        """Local SSH credential check"""
        username = config.get("username", "user")
        password = config.get("password", "password123")
        
        # Check if sshpass is available
        try:
            subprocess.run(["which", "sshpass"], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                exploit_type="CREDENTIAL",
                target_ip=target_ip,
                evidence="sshpass not installed - install with: apt install sshpass"
            )
        
        cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {username}@{target_ip} 'echo SUCCESS'"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=min(30, timeout)
            )
            
            success = "SUCCESS" in result.stdout
            return ValidationResult(
                status=ValidationStatus.SUCCESS if success else ValidationStatus.FAILED,
                exploit_type="CREDENTIAL",
                target_ip=target_ip,
                evidence=f"SSH {'succeeded' if success else 'failed'} with {username}:{password}",
                details={"username": username, "method": "sshpass"}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="CREDENTIAL",
                target_ip=target_ip,
                evidence="SSH check timed out"
            )
    
    async def _local_smb_check(self, target_ip: str, timeout: int) -> ValidationResult:
        """Local SMB check"""
        try:
            subprocess.run(["which", "smbclient"], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                exploit_type="NETWORK",
                target_ip=target_ip,
                evidence="smbclient not installed"
            )
        
        cmd = f"smbclient -L //{target_ip} -N 2>&1"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=min(30, timeout)
            )
            
            has_shares = "Disk" in result.stdout or "Sharename" in result.stdout
            return ValidationResult(
                status=ValidationStatus.SUCCESS if has_shares else ValidationStatus.FAILED,
                exploit_type="NETWORK",
                target_ip=target_ip,
                evidence=result.stdout[:500]
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="NETWORK",
                target_ip=target_ip,
                evidence="SMB check timed out"
            )
    
    async def _local_web_check(
        self,
        target_ip: str,
        config: Dict,
        timeout: int
    ) -> ValidationResult:
        """Local web check using curl"""
        port = config.get("port", 80)
        
        cmd = f"curl -s --connect-timeout 10 -o /dev/null -w '%{{http_code}}' http://{target_ip}:{port}/"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=min(20, timeout)
            )
            
            status_code = result.stdout.strip()
            success = status_code.startswith("2") or status_code.startswith("3")
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if success else ValidationStatus.FAILED,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence=f"HTTP status: {status_code}",
                details={"port": port, "status_code": status_code}
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="WEB",
                target_ip=target_ip,
                evidence="Web check timed out"
            )
    
    async def _local_ping_check(self, target_ip: str, timeout: int) -> ValidationResult:
        """Simple ping check"""
        cmd = f"ping -c 1 -W 5 {target_ip}"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=min(10, timeout)
            )
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS if result.returncode == 0 else ValidationStatus.FAILED,
                exploit_type="UNKNOWN",
                target_ip=target_ip,
                evidence="Target reachable" if result.returncode == 0 else "Target unreachable"
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                exploit_type="UNKNOWN",
                target_ip=target_ip,
                evidence="Ping timed out"
            )
    
    async def validate_multiple(
        self,
        target_ip: str,
        exploits: List[Dict[str, Any]],
        timeout_per_exploit: int = 120
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple exploits on a target.
        
        Returns dict mapping exploit name/id to ValidationResult
        """
        results = {}
        
        for exploit in exploits:
            exploit_id = exploit.get("id") or exploit.get("name", "unknown")
            result = await self.validate(target_ip, exploit, timeout_per_exploit)
            results[str(exploit_id)] = result
            
            # Log progress
            status_icon = "✅" if result.status == ValidationStatus.SUCCESS else "❌"
            logger.info(f"{status_icon} {exploit.get('name', exploit_id)}: {result.status.value}")
        
        return results


# Convenience function
async def validate_exploit(
    target_ip: str,
    exploit_config: Dict[str, Any],
    use_docker: bool = True
) -> ValidationResult:
    """Quick validation helper"""
    client = WhiteKnightClient(use_docker=use_docker)
    return await client.validate(target_ip, exploit_config)

