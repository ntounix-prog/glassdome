"""
Mailcow API Client

Handles mailbox creation, email monitoring (IMAP), and email sending (SMTP)
for the xisx.org domain.
"""
import logging
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from email.header import decode_header

logger = logging.getLogger(__name__)


class MailcowClient:
    """Client for Mailcow API operations"""
    
    def __init__(
        self,
        api_url: str,
        api_token: str,
        domain: str = "xisx.org",
        imap_host: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        verify_ssl: bool = False
    ):
        """
        Initialize Mailcow client
        
        Args:
            api_url: Mailcow API URL (e.g., https://mail.xisx.org)
            api_token: Mailcow API Bearer token (from MAIL_API)
            domain: Domain for mailboxes (default: xisx.org)
            imap_host: IMAP server hostname/IP (defaults to API URL host)
            smtp_host: SMTP server hostname/IP (defaults to API URL host)
            smtp_port: SMTP port (default: 587)
            verify_ssl: Whether to verify SSL certificates (default: False)
        """
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.domain = domain
        self.domain = domain
        
        # Extract host from API URL (IP or hostname)
        from urllib.parse import urlparse
        parsed = urlparse(self.api_url)
        api_host = parsed.hostname or parsed.path.split('/')[0] or 'localhost'
        
        self.imap_host = imap_host or api_host
        self.imap_port = 993  # IMAP SSL port
        self.smtp_host = smtp_host or api_host
        self.smtp_port = smtp_port
        self.verify_ssl = verify_ssl
        
        # Mailcow uses X-API-Key header (not Bearer token)
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_token
        }
        
        # Disable SSL warnings if verification is disabled
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def create_mailbox(
        self,
        local_part: str,
        password: str,
        name: str,
        quota_mb: int = 1024,
        active: bool = True,
        force_pw_update: bool = False,
        tls_enforce_in: bool = True,
        tls_enforce_out: bool = True
    ) -> Dict[str, Any]:
        """
        Create a mailbox via Mailcow API
        
        Args:
            local_part: Username part (before @)
            password: Mailbox password (must meet complexity requirements)
            name: Display name
            quota_mb: Mailbox quota in MB (default: 1024)
            active: Whether mailbox is active (default: True)
            force_pw_update: Force password update on first login (default: False)
            tls_enforce_in: Enforce TLS for incoming (default: True)
            tls_enforce_out: Enforce TLS for outgoing (default: True)
            
        Returns:
            Result dictionary with success status and mailbox details
        """
        url = f"{self.api_url}/api/v1/add/mailbox"
        
        data = {
            'active': '1' if active else '0',  # Mailcow expects strings
            'domain': self.domain,
            'local_part': local_part,
            'name': name,
            'password': password,
            'password2': password,  # Required: password confirmation
            'quota': str(quota_mb),  # Mailcow expects string
            'force_pw_update': '1' if force_pw_update else '0',
            'tls_enforce_in': '1' if tls_enforce_in else '0',
            'tls_enforce_out': '1' if tls_enforce_out else '0'
        }
        
        try:
            logger.info(f"Creating mailbox {local_part}@{self.domain}")
            response = requests.post(url, json=data, headers=self.headers, timeout=30, verify=self.verify_ssl)
            
            # Check response
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(f"Response text: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    # Mailcow returns array of responses, check if all are success
                    if isinstance(result, list):
                        # Check each response in the array
                        errors = []
                        for item in result:
                            if isinstance(item, dict):
                                response_type = item.get('type', '')
                                if response_type in ['danger', 'error']:
                                    # Extract error message
                                    msg = item.get('msg', [])
                                    if isinstance(msg, list):
                                        error_msg = ' '.join(str(m) for m in msg)
                                    else:
                                        error_msg = str(msg)
                                    errors.append(error_msg)
                        
                        if errors:
                            error_text = '; '.join(errors)
                            logger.error(f"❌ Failed to create mailbox: {error_text}")
                            return {
                                'success': False,
                                'error': error_text,
                                'details': result
                            }
                        else:
                            # All responses are success
                            logger.info(f"✅ Mailbox created: {local_part}@{self.domain}")
                            return {
                                'success': True,
                                'mailbox': f"{local_part}@{self.domain}",
                                'details': result
                            }
                    elif isinstance(result, dict):
                        # Single response object
                        response_type = result.get('type', '')
                        if response_type in ['danger', 'error']:
                            msg = result.get('msg', [])
                            error_msg = ' '.join(str(m) for m in msg) if isinstance(msg, list) else str(msg)
                            logger.error(f"❌ Failed to create mailbox: {error_msg}")
                            return {
                                'success': False,
                                'error': error_msg,
                                'details': result
                            }
                        else:
                            logger.info(f"✅ Mailbox created: {local_part}@{self.domain}")
                            return {
                                'success': True,
                                'mailbox': f"{local_part}@{self.domain}",
                                'details': result
                            }
                    else:
                        # Unexpected format, but status is 200
                        logger.warning(f"⚠️  Unexpected response format: {result}")
                        return {
                            'success': True,  # Assume success if 200
                            'mailbox': f"{local_part}@{self.domain}",
                            'details': result
                        }
                except ValueError:
                    # Not JSON, might be success message
                    if 'success' in response.text.lower() or response.status_code == 200:
                        logger.info(f"✅ Mailbox created: {local_part}@{self.domain} (non-JSON response)")
                        return {
                            'success': True,
                            'mailbox': f"{local_part}@{self.domain}",
                            'details': {'message': response.text}
                        }
                    else:
                        logger.error(f"❌ Unexpected response: {response.text[:200]}")
                        return {
                            'success': False,
                            'error': f'Unexpected response: {response.text[:200]}',
                            'status_code': response.status_code
                        }
            else:
                try:
                    error_msg = response.json().get('msg', response.text[:200])
                except ValueError:
                    error_msg = response.text[:200] or f'HTTP {response.status_code}'
                logger.error(f"❌ Failed to create mailbox: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"❌ Exception creating mailbox: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_mailbox_messages(
        self,
        mailbox: str,
        password: str,
        folder: str = 'INBOX',
        unread_only: bool = True
    ) -> Dict[str, Any]:
        """
        Get messages from mailbox via IMAP
        
        Args:
            mailbox: Full email address (e.g., user@xisx.org)
            password: Mailbox password
            folder: IMAP folder (default: INBOX)
            unread_only: Only fetch unread messages (default: True)
            
        Returns:
            Dictionary with messages list and metadata
        """
        try:
            logger.info(f"Connecting to IMAP: {self.imap_host}:{self.imap_port}")
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(mailbox, password)
            mail.select(folder)
            
            # Search for messages
            if unread_only:
                status, messages = mail.search(None, 'UNSEEN')
            else:
                status, messages = mail.search(None, 'ALL')
            
            if status != 'OK':
                logger.error(f"IMAP search failed: {messages}")
                mail.logout()
                return {
                    'success': False,
                    'error': 'IMAP search failed',
                    'messages': []
                }
            
            message_ids = messages[0].split()
            message_list = []
            
            for msg_id in message_ids:
                try:
                    status, data = mail.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    raw_email = data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    # Parse email
                    subject = self._decode_header(email_message['Subject'] or 'No Subject')
                    from_addr = email_message['From'] or 'Unknown'
                    to_addr = email_message['To'] or 'Unknown'
                    date = email_message['Date'] or 'Unknown'
                    
                    # Get body
                    body = self._get_email_body(email_message)
                    
                    message_list.append({
                        'id': msg_id.decode(),
                        'subject': subject,
                        'from': from_addr,
                        'to': to_addr,
                        'date': date,
                        'body': body,
                        'raw': raw_email.decode('utf-8', errors='ignore')
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing message {msg_id}: {e}")
                    continue
            
            mail.logout()
            
            logger.info(f"✅ Retrieved {len(message_list)} messages from {mailbox}")
            return {
                'success': True,
                'mailbox': mailbox,
                'count': len(message_list),
                'messages': message_list
            }
            
        except imaplib.IMAP4.error as e:
            logger.error(f"❌ IMAP error: {e}")
            return {
                'success': False,
                'error': f'IMAP error: {str(e)}',
                'messages': []
            }
        except Exception as e:
            logger.error(f"❌ Exception getting messages: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'messages': []
            }
    
    def send_email(
        self,
        mailbox: str,
        password: Optional[str] = None,
        to_addresses: List[str] = None,
        subject: str = "",
        body: str = "",
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        use_api: bool = True
    ) -> Dict[str, Any]:
        """
        Send email via Mailcow API or SMTP
        
        Args:
            mailbox: Sender email address (e.g., user@xisx.org)
            password: Mailbox password (not needed for API, required for SMTP)
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            use_api: Use Mailcow API instead of SMTP (default: True)
            
        Returns:
            Result dictionary with success status
        """
        # Try API first (more reliable)
        if use_api:
            return self._send_email_api(mailbox, to_addresses, subject, body, html_body, cc, bcc)
        
        # Fallback to SMTP
        return self._send_email_smtp(mailbox, password, to_addresses, subject, body, html_body, cc, bcc)
    
    def _send_email_api(
        self,
        mailbox: str,
        to_addresses: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send email via Mailcow API"""
        url = f"{self.api_url}/api/v1/send/mail"
        
        # Build recipients
        recipients = to_addresses.copy() if to_addresses else []
        if cc:
            recipients.extend(cc)
        if bcc:
            recipients.extend(bcc)
        
        data = {
            'from': mailbox,
            'to': recipients,
            'subject': subject,
            'text': body
        }
        
        if html_body:
            data['html'] = html_body
        
        try:
            logger.info(f"Sending email via API from {mailbox} to {', '.join(to_addresses)}")
            response = requests.post(url, json=data, headers=self.headers, timeout=30, verify=self.verify_ssl)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                except ValueError:
                    result = {'message': response.text}
                
                logger.info(f"✅ Email sent successfully via API")
                return {
                    'success': True,
                    'from': mailbox,
                    'to': to_addresses,
                    'subject': subject,
                    'sent_at': datetime.now().isoformat(),
                    'method': 'api'
                }
            else:
                error_text = response.text[:200] if response.text else f'HTTP {response.status_code}'
                logger.error(f"❌ Failed to send email via API: {error_text}")
                return {
                    'success': False,
                    'error': f'API error: {error_text}',
                    'status_code': response.status_code
                }
        except Exception as e:
            logger.error(f"❌ Exception sending email via API: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_email_smtp(
        self,
        mailbox: str,
        password: str,
        to_addresses: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send email via SMTP (fallback)"""
        try:
            # Create message
            if html_body:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body, 'plain'))
                msg.attach(MIMEText(html_body, 'html'))
            else:
                msg = MIMEText(body)
            
            msg['Subject'] = subject
            msg['From'] = mailbox
            msg['To'] = ', '.join(to_addresses)
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            # Connect and send
            logger.info(f"Connecting to SMTP: {self.smtp_host}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(mailbox, password)
            
            recipients = to_addresses.copy()
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            server.sendmail(mailbox, recipients, msg.as_string())
            server.quit()
            
            logger.info(f"✅ Email sent from {mailbox} to {', '.join(to_addresses)}")
            return {
                'success': True,
                'from': mailbox,
                'to': to_addresses,
                'subject': subject,
                'sent_at': datetime.now().isoformat()
            }
            
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return {
                'success': False,
                'error': f'SMTP error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"❌ Exception sending email: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_mailboxes(self) -> Dict[str, Any]:
        """
        List all mailboxes for the domain
        
        Returns:
            Dictionary with mailbox list
        """
        # Updated endpoint format from OpenAPI spec: /api/v1/get/mailbox/all/{domain}
        url = f"{self.api_url}/api/v1/get/mailbox/all/{self.domain}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30, verify=self.verify_ssl)
            
            logger.debug(f"List mailboxes response status: {response.status_code}")
            logger.debug(f"Response text: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    mailboxes = response.json()
                    # API returns list directly for domain-specific endpoint
                    if isinstance(mailboxes, list):
                        return {
                            'success': True,
                            'count': len(mailboxes),
                            'mailboxes': mailboxes
                        }
                    else:
                        # Handle dict response (error or different format)
                        error_msg = mailboxes.get('msg', 'Unknown error') if isinstance(mailboxes, dict) else str(mailboxes)
                        logger.error(f"❌ Unexpected response format: {error_msg}")
                        return {
                            'success': False,
                            'error': error_msg,
                            'status_code': response.status_code
                        }
                except ValueError:
                    logger.error(f"❌ Non-JSON response: {response.text[:200]}")
                    return {
                        'success': False,
                        'error': f'Non-JSON response: {response.text[:200]}',
                        'status_code': response.status_code
                    }
            else:
                error_text = response.text[:200] if response.text else 'No response body'
                return {
                    'success': False,
                    'error': f'API error {response.status_code}: {error_text}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"❌ Exception listing mailboxes: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_mailbox(self, mailbox_id: int) -> Dict[str, Any]:
        """
        Delete a mailbox via Mailcow API
        
        Args:
            mailbox_id: Mailbox ID from Mailcow
            
        Returns:
            Result dictionary
        """
        url = f"{self.api_url}/api/v1/delete/mailbox"
        
        data = {
            'items': [mailbox_id]
        }
        
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=30, verify=self.verify_ssl)
            
            if response.status_code == 200:
                logger.info(f"✅ Mailbox {mailbox_id} deleted")
                return {
                    'success': True,
                    'mailbox_id': mailbox_id
                }
            else:
                error_msg = response.json().get('msg', 'Unknown error')
                logger.error(f"❌ Failed to delete mailbox: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Exception deleting mailbox: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _decode_header(self, header: str) -> str:
        """Decode email header (handles encoded words)"""
        if not header:
            return ''
        
        decoded_parts = decode_header(header)
        decoded_str = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_str += part
        return decoded_str
    
    def _get_email_body(self, email_message) -> str:
        """Extract email body (text or HTML)"""
        body = ''
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                elif content_type == 'text/html' and not body:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            content_type = email_message.get_content_type()
            if content_type in ['text/plain', 'text/html']:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return body

