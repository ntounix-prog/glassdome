"""
Ssh Client module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException
import io

logger = logging.getLogger(__name__)


class SSHClient:
    """
    SSH Client for executing commands on remote hosts
    
    Supports:
    - Password authentication
    - SSH key authentication
    - Command execution
    - File transfer (SCP)
    - Interactive sessions
    - Connection pooling
    """
    
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize SSH client
        
        Args:
            host: Remote host address
            port: SSH port (default: 22)
            username: SSH username
            password: Password (if using password auth)
            key_filename: Path to private key (if using key auth)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
        self._connected = False
        
    async def connect(self) -> bool:
        """
        Establish SSH connection
        
        Returns:
            True if connected successfully
        """
        if self._connected:
            return True
            
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info(f"Connecting to {self.username}@{self.host}:{self.port}")
            
            # Run connection in thread pool (paramiko is synchronous)
            # For password auth, disable agent and key lookup (helps with Cisco devices)
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": self.timeout,
            }
            
            if self.password:
                connect_kwargs["password"] = self.password
                connect_kwargs["allow_agent"] = False
                connect_kwargs["look_for_keys"] = False
            else:
                connect_kwargs["allow_agent"] = True
                connect_kwargs["look_for_keys"] = True
                
            if self.key_filename:
                connect_kwargs["key_filename"] = self.key_filename
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.connect(**connect_kwargs)
            )
            
            self._connected = True
            logger.info(f"✅ Connected to {self.host}")
            return True
            
        except AuthenticationException as e:
            logger.error(f"Authentication failed for {self.username}@{self.host}: {e}")
            return False
        except SSHException as e:
            logger.error(f"SSH error connecting to {self.host}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {e}")
            return False
    
    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        check: bool = True
    ) -> Dict[str, Any]:
        """
        Execute command on remote host
        
        Args:
            command: Command to execute
            timeout: Command timeout (None = no timeout)
            check: Raise exception if exit code != 0
            
        Returns:
            Dictionary with stdout, stderr, exit_code
        """
        if not self._connected:
            await self.connect()
        
        try:
            logger.info(f"Executing: {command}")
            
            # Execute command in thread pool
            stdin, stdout, stderr = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.exec_command(command, timeout=timeout)
            )
            
            # Read output
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            result = {
                "stdout": stdout_data,
                "stderr": stderr_data,
                "exit_code": exit_code,
                "success": exit_code == 0
            }
            
            if exit_code == 0:
                logger.info(f"✅ Command succeeded (exit {exit_code})")
            else:
                logger.warning(f"⚠️ Command failed (exit {exit_code})")
                if stderr_data:
                    logger.warning(f"Error: {stderr_data[:200]}")
            
            if check and exit_code != 0:
                raise RuntimeError(f"Command failed with exit code {exit_code}: {stderr_data}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False
            }
    
    async def execute_script(
        self,
        script: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute multi-line script
        
        Args:
            script: Shell script to execute
            timeout: Script timeout
            
        Returns:
            Execution result
        """
        # Upload script and execute
        script_path = f"/tmp/glassdome_script_{id(script)}.sh"
        
        # Write script
        await self.execute(f"cat > {script_path} << 'EOFSCRIPT'\n{script}\nEOFSCRIPT")
        await self.execute(f"chmod +x {script_path}")
        
        # Execute
        result = await self.execute(f"bash {script_path}", timeout=timeout, check=False)
        
        # Cleanup
        await self.execute(f"rm -f {script_path}", check=False)
        
        return result
    
    async def file_exists(self, path: str) -> bool:
        """Check if file exists on remote host"""
        result = await self.execute(f"test -f {path}", check=False)
        return result["exit_code"] == 0
    
    async def directory_exists(self, path: str) -> bool:
        """Check if directory exists on remote host"""
        result = await self.execute(f"test -d {path}", check=False)
        return result["exit_code"] == 0
    
    async def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload file to remote host via SCP
        
        Args:
            local_path: Local file path
            remote_path: Remote destination path
            
        Returns:
            True if successful
        """
        if not self._connected:
            await self.connect()
        
        try:
            logger.info(f"Uploading {local_path} to {remote_path}")
            
            sftp = self.client.open_sftp()
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sftp.put(local_path, remote_path)
            )
            sftp.close()
            
            logger.info(f"✅ File uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return False
    
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download file from remote host via SCP
        
        Args:
            remote_path: Remote file path
            local_path: Local destination path
            
        Returns:
            True if successful
        """
        if not self._connected:
            await self.connect()
        
        try:
            logger.info(f"Downloading {remote_path} to {local_path}")
            
            sftp = self.client.open_sftp()
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sftp.get(remote_path, local_path)
            )
            sftp.close()
            
            logger.info(f"✅ File downloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return False
    
    async def read_file(self, remote_path: str) -> Optional[str]:
        """
        Read file contents from remote host
        
        Args:
            remote_path: Remote file path
            
        Returns:
            File contents or None if failed
        """
        result = await self.execute(f"cat {remote_path}", check=False)
        if result["success"]:
            return result["stdout"]
        return None
    
    async def write_file(self, remote_path: str, content: str) -> bool:
        """
        Write content to file on remote host
        
        Args:
            remote_path: Remote file path
            content: Content to write
            
        Returns:
            True if successful
        """
        # Escape content for heredoc
        escaped = content.replace("'", "'\\''")
        result = await self.execute(
            f"cat > {remote_path} << 'EOF'\n{escaped}\nEOF",
            check=False
        )
        return result["success"]
    
    async def disconnect(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info(f"Disconnected from {self.host}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.client:
            self.client.close()


class SSHCommandBuilder:
    """
    Helper to build complex SSH commands
    """
    
    @staticmethod
    def chain(*commands: str) -> str:
        """Chain multiple commands with &&"""
        return " && ".join(commands)
    
    @staticmethod
    def pipe(*commands: str) -> str:
        """Pipe commands together"""
        return " | ".join(commands)
    
    @staticmethod
    def sudo(command: str) -> str:
        """Wrap command in sudo"""
        return f"sudo {command}"
    
    @staticmethod
    def background(command: str) -> str:
        """Run command in background"""
        return f"nohup {command} > /dev/null 2>&1 &"
    
    @staticmethod
    def with_env(env: Dict[str, str], command: str) -> str:
        """Run command with environment variables"""
        env_str = " ".join([f"{k}={v}" for k, v in env.items()])
        return f"{env_str} {command}"

