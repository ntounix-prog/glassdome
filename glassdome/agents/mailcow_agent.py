"""
Mailcow Agent

Autonomous agent for managing mailboxes and email operations on xisx.org domain.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from glassdome.agents.base import BaseAgent, AgentType, AgentStatus
from glassdome.integrations.mailcow_client import MailcowClient

logger = logging.getLogger(__name__)


class MailcowAgent(BaseAgent):
    """Agent for Mailcow mailbox and email management"""
    
    def __init__(
        self,
        agent_id: str,
        api_url: str,
        api_token: str,
        domain: str = "xisx.org",
        imap_host: Optional[str] = None,
        smtp_host: Optional[str] = None,
        verify_ssl: bool = False
    ):
        """
        Initialize Mailcow agent
        
        Args:
            agent_id: Unique agent identifier
            api_url: Mailcow API URL (e.g., https://mail.xisx.org)
            api_token: Mailcow API Bearer token (from MAIL_API)
            domain: Domain for mailboxes (default: xisx.org)
            imap_host: IMAP server hostname/IP (optional)
            smtp_host: SMTP server hostname/IP (optional)
            verify_ssl: Whether to verify SSL certificates (default: False)
        """
        super().__init__(agent_id, AgentType.MONITORING)
        self.client = MailcowClient(
            api_url=api_url,
            api_token=api_token,
            domain=domain,
            imap_host=imap_host,
            smtp_host=smtp_host,
            verify_ssl=verify_ssl
        )
        self.domain = domain
        self.monitored_mailboxes: Dict[str, Dict[str, Any]] = {}
    
    def validate(self, task: Dict[str, Any]) -> bool:
        """
        Validate task parameters
        
        Args:
            task: Task definition
            
        Returns:
            True if valid, False otherwise
        """
        action = task.get('action')
        if not action:
            return False
        
        valid_actions = [
            'create_mailbox',
            'monitor_mailbox',
            'send_email',
            'list_mailboxes',
            'delete_mailbox'
        ]
        
        if action not in valid_actions:
            return False
        
        # Action-specific validation
        if action == 'create_mailbox':
            return bool(task.get('local_part') and task.get('password'))
        elif action == 'monitor_mailbox':
            return bool(task.get('mailbox') and task.get('password'))
        elif action == 'send_email':
            return bool(
                task.get('mailbox') and
                task.get('password') and
                task.get('to_addresses') and
                task.get('subject')
            )
        elif action == 'delete_mailbox':
            return bool(task.get('mailbox_id'))
        
        return True
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Mailcow agent task
        
        Task types:
        - create_mailbox: Create a new mailbox
        - monitor_mailbox: Check for new emails in a mailbox
        - send_email: Send an email from a mailbox
        - list_mailboxes: List all mailboxes on domain
        - delete_mailbox: Delete a mailbox
        
        Args:
            task: Task definition with 'action' and parameters
            
        Returns:
            Result dictionary
        """
        self.status = AgentStatus.RUNNING
        
        try:
            action = task.get('action')
            
            if action == 'create_mailbox':
                return await self._create_mailbox(task)
            elif action == 'monitor_mailbox':
                return await self._monitor_mailbox(task)
            elif action == 'send_email':
                return await self._send_email(task)
            elif action == 'list_mailboxes':
                return await self._list_mailboxes(task)
            elif action == 'delete_mailbox':
                return await self._delete_mailbox(task)
            else:
                return {
                    'success': False,
                    'error': f'Unknown action: {action}',
                    'available_actions': [
                        'create_mailbox',
                        'monitor_mailbox',
                        'send_email',
                        'list_mailboxes',
                        'delete_mailbox'
                    ]
                }
                
        except Exception as e:
            logger.error(f"❌ Error executing task: {e}", exc_info=True)
            self.status = AgentStatus.FAILED
            self.error = str(e)
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if self.status != AgentStatus.FAILED:
                self.status = AgentStatus.COMPLETED
    
    async def _create_mailbox(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mailbox"""
        local_part = task.get('local_part')
        password = task.get('password')
        name = task.get('name', local_part)
        quota_mb = task.get('quota_mb', 1024)
        
        if not local_part or not password:
            return {
                'success': False,
                'error': 'local_part and password are required'
            }
        
        result = self.client.create_mailbox(
            local_part=local_part,
            password=password,
            name=name,
            quota_mb=quota_mb
        )
        
        if result.get('success'):
            # Store mailbox for monitoring
            mailbox = result['mailbox']
            self.monitored_mailboxes[mailbox] = {
                'password': password,
                'created_at': datetime.now().isoformat(),
                'last_checked': None
            }
        
        return result
    
    async def _monitor_mailbox(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor mailbox for new emails"""
        mailbox = task.get('mailbox')
        password = task.get('password')
        unread_only = task.get('unread_only', True)
        folder = task.get('folder', 'INBOX')
        
        if not mailbox or not password:
            return {
                'success': False,
                'error': 'mailbox and password are required'
            }
        
        # Ensure mailbox is in monitored list
        if mailbox not in self.monitored_mailboxes:
            self.monitored_mailboxes[mailbox] = {
                'password': password,
                'created_at': datetime.now().isoformat(),
                'last_checked': None
            }
        else:
            # Update password if provided
            if password:
                self.monitored_mailboxes[mailbox]['password'] = password
        
        result = self.client.get_mailbox_messages(
            mailbox=mailbox,
            password=password,
            folder=folder,
            unread_only=unread_only
        )
        
        if result.get('success'):
            self.monitored_mailboxes[mailbox]['last_checked'] = datetime.now().isoformat()
        
        return result
    
    async def _send_email(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Send email from a mailbox"""
        mailbox = task.get('mailbox')
        password = task.get('password')  # Optional for API, required for SMTP
        to_addresses = task.get('to_addresses', [])
        subject = task.get('subject', '')
        body = task.get('body', '')
        html_body = task.get('html_body')
        cc = task.get('cc')
        bcc = task.get('bcc')
        use_api = task.get('use_api', True)  # Default to API
        
        if not mailbox:
            return {
                'success': False,
                'error': 'mailbox is required'
            }
        
        if not to_addresses:
            return {
                'success': False,
                'error': 'to_addresses is required'
            }
        
        if not isinstance(to_addresses, list):
            to_addresses = [to_addresses]
        
        # Password only required for SMTP
        if not use_api and not password:
            return {
                'success': False,
                'error': 'password is required for SMTP (set use_api=True to use API)'
            }
        
        result = self.client.send_email(
            mailbox=mailbox,
            password=password,
            to_addresses=to_addresses,
            subject=subject,
            body=body,
            html_body=html_body,
            cc=cc,
            bcc=bcc,
            use_api=use_api
        )
        
        return result
    
    async def _list_mailboxes(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List all mailboxes on domain"""
        result = self.client.list_mailboxes()
        return result
    
    async def _delete_mailbox(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a mailbox"""
        mailbox_id = task.get('mailbox_id')
        
        if not mailbox_id:
            return {
                'success': False,
                'error': 'mailbox_id is required'
            }
        
        result = self.client.delete_mailbox(mailbox_id)
        
        if result.get('success'):
            # Remove from monitored list if present
            for mailbox, info in list(self.monitored_mailboxes.items()):
                # Note: We'd need to match by ID, but we store by email
                # For now, just log
                pass
        
        return result
    
    async def monitor_all_mailboxes(self) -> Dict[str, Any]:
        """
        Monitor all registered mailboxes for new emails
        
        Returns:
            Dictionary with results for each mailbox
        """
        results = {}
        
        for mailbox, info in self.monitored_mailboxes.items():
            password = info['password']
            result = await self._monitor_mailbox({
                'mailbox': mailbox,
                'password': password,
                'unread_only': True
            })
            results[mailbox] = result
        
        return {
            'success': True,
            'mailboxes_checked': len(results),
            'results': results
        }

