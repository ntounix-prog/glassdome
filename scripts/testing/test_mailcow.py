#!/usr/bin/env python3
"""
Test Mailcow Agent

Tests mailbox creation, monitoring, and email sending on xisx.org domain.
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()

from glassdome.agents.mailcow_agent import MailcowAgent

# Use centralized logging
try:
    from glassdome.core.logging import setup_logging_from_settings
    setup_logging_from_settings()
except ImportError:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_mailcow_agent():
    """Test Mailcow agent operations"""
    
    # Load session-aware settings
    settings = get_secure_settings()
    
    if not settings.mail_api:
        logger.error("❌ Mailcow API token not configured. Check .env file.")
        logger.info("Required settings:")
        logger.info("  MAIL_API=your-bearer-token")
        logger.info("  MAILCOW_API_URL=https://mail.xisx.org")
        return
    
    # Use domain name if API URL not set
    api_url = settings.mailcow_api_url or f"https://mail.{settings.mailcow_domain}"
    
    # Initialize agent
    agent = MailcowAgent(
        agent_id="mailcow-test-agent",
        api_url=api_url,
        api_token=settings.mail_api,
        domain=settings.mailcow_domain,
        imap_host=settings.mailcow_imap_host,
        smtp_host=settings.mailcow_smtp_host,
        verify_ssl=settings.mailcow_verify_ssl
    )
    
    logger.info("=" * 70)
    logger.info("Mailcow Agent Test")
    logger.info("=" * 70)
    logger.info(f"Domain: {settings.mailcow_domain}")
    logger.info(f"API URL: {api_url}")
    logger.info(f"API Token: {'*' * 20} (hidden)")
    print()
    
    # Test 1: List existing mailboxes
    logger.info("📋 Test 1: List existing mailboxes")
    logger.info("-" * 70)
    result = await agent.execute({
        'action': 'list_mailboxes'
    })
    
    if result.get('success'):
        logger.info(f"✅ Found {result.get('count', 0)} mailboxes")
        for mb in result.get('mailboxes', [])[:5]:  # Show first 5
            logger.info(f"   - {mb.get('username', 'N/A')}@{mb.get('domain', 'N/A')}")
    else:
        logger.error(f"❌ Failed: {result.get('error')}")
    print()
    
    # Test 2: Create a test mailbox
    logger.info("📧 Test 2: Create test mailbox")
    logger.info("-" * 70)
    test_mailbox = f"glassdome-test@{settings.mailcow_domain}"
    # Use password from environment or default
    import os
    test_password = os.getenv('TEST_MAILBOX_PASSWORD', 'GlassdomeTest123!')
    logger.info(f"   Using password: {test_password[:3]}*** (set TEST_MAILBOX_PASSWORD env var to change)")
    
    result = await agent.execute({
        'action': 'create_mailbox',
        'local_part': 'glassdome-test',
        'password': test_password,
        'name': 'Glassdome Test Mailbox',
        'quota_mb': 512
    })
    
    if result.get('success'):
        logger.info(f"✅ Mailbox created: {test_mailbox}")
        mailbox_created = True
    else:
        logger.error(f"❌ Failed to create mailbox: {result.get('error')}")
        if 'already exists' in result.get('error', '').lower():
            logger.info("   (Mailbox may already exist, continuing with tests)")
            mailbox_created = True
        else:
            mailbox_created = False
    print()
    
    if not mailbox_created:
        logger.warning("⚠️  Skipping remaining tests (mailbox creation failed)")
        return
    
    # Test 3: Send test email
    logger.info("📤 Test 3: Send test email")
    logger.info("-" * 70)
    test_recipient = "ntounix@gmail.com"
    logger.info(f"   Sending to: {test_recipient}")
    logger.info(f"   Using SMTP (not API - Mailcow doesn't have send email API)")
    
    result = await agent.execute({
        'action': 'send_email',
        'mailbox': test_mailbox,
        'password': test_password,
        'to_addresses': [test_recipient],
        'use_api': False,  # Use SMTP, not API
        'subject': 'Glassdome Mailcow Agent Test',
        'body': f'''This is a test email from the Glassdome Mailcow agent.

Mailbox: {test_mailbox}
Domain: {settings.mailcow_domain}
API URL: {api_url}

If you receive this email, the Mailcow agent is working correctly!

The agent can:
- Create mailboxes via Mailcow API
- Monitor mailboxes for new emails via IMAP
- Send emails via SMTP

This test was run on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
''',
        'html_body': f'''<html>
<body>
    <h1>Glassdome Mailcow Agent Test</h1>
    <p>This is a test email from the Glassdome Mailcow agent.</p>
    <ul>
        <li><strong>Mailbox:</strong> {test_mailbox}</li>
        <li><strong>Domain:</strong> {settings.mailcow_domain}</li>
        <li><strong>API URL:</strong> {api_url}</li>
    </ul>
    <p>If you receive this email, the Mailcow agent is working correctly!</p>
    <p>The agent can:</p>
    <ul>
        <li>Create mailboxes via Mailcow API</li>
        <li>Monitor mailboxes for new emails via IMAP</li>
        <li>Send emails via SMTP</li>
    </ul>
    <p><em>Test run on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</em></p>
</body>
</html>'''
    })
    
    if result.get('success'):
        logger.info(f"✅ Email sent successfully")
        logger.info(f"   From: {result.get('from')}")
        logger.info(f"   To: {', '.join(result.get('to', []))}")
        logger.info(f"   Sent at: {result.get('sent_at')}")
    else:
        logger.error(f"❌ Failed to send email: {result.get('error')}")
    print()
    
    # Wait a moment for email to arrive
    logger.info("⏳ Waiting 5 seconds for email to arrive...")
    await asyncio.sleep(5)
    print()
    
    # Test 4: Monitor mailbox for new emails
    logger.info("📥 Test 4: Monitor mailbox for new emails")
    logger.info("-" * 70)
    result = await agent.execute({
        'action': 'monitor_mailbox',
        'mailbox': test_mailbox,
        'password': test_password,
        'unread_only': True
    })
    
    if result.get('success'):
        count = result.get('count', 0)
        logger.info(f"✅ Found {count} unread message(s)")
        
        messages = result.get('messages', [])
        for msg in messages[:3]:  # Show first 3
            logger.info(f"   Message {msg.get('id')}:")
            logger.info(f"      Subject: {msg.get('subject')}")
            logger.info(f"      From: {msg.get('from')}")
            logger.info(f"      Date: {msg.get('date')}")
            logger.info(f"      Body preview: {msg.get('body', '')[:100]}...")
    else:
        logger.error(f"❌ Failed to monitor mailbox: {result.get('error')}")
    print()
    
    # Test 5: Monitor all registered mailboxes
    logger.info("🔄 Test 5: Monitor all registered mailboxes")
    logger.info("-" * 70)
    result = await agent.monitor_all_mailboxes()
    
    if result.get('success'):
        logger.info(f"✅ Monitored {result.get('mailboxes_checked', 0)} mailbox(es)")
        for mailbox, mb_result in result.get('results', {}).items():
            if mb_result.get('success'):
                count = mb_result.get('count', 0)
                logger.info(f"   {mailbox}: {count} unread message(s)")
            else:
                logger.warning(f"   {mailbox}: Error - {mb_result.get('error')}")
    print()
    
    logger.info("=" * 70)
    logger.info("✅ Mailcow Agent Test Complete")
    logger.info("=" * 70)
    print()
    logger.info("📋 Summary:")
    logger.info(f"   - Mailbox: {test_mailbox}")
    logger.info(f"   - Password: {test_password}")
    logger.info(f"   - Domain: {settings.mailcow_domain}")
    logger.info(f"   - Agent ID: {agent.agent_id}")
    print()
    logger.info("💡 Next Steps:")
    logger.info("   - Check ntounix@gmail.com for test email")
    logger.info("   - Use agent.monitor_all_mailboxes() for continuous monitoring")
    logger.info("   - Integrate with Overseer for autonomous email operations")


if __name__ == "__main__":
    asyncio.run(test_mailcow_agent())

