"""
Cli module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import click
import asyncio
import getpass
from pathlib import Path
from glassdome import __version__
from glassdome.core.config import settings
from glassdome.core.secrets import get_secrets_manager


@click.group()
@click.version_option(version=__version__)
def main():
    """Glassdome - Agentic Cyber Range Deployment Framework"""
    pass


@main.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8010, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host, port, reload):
    """Start the Glassdome API server"""
    import uvicorn
    click.echo(f"Starting Glassdome API server on {host}:{port}")
    uvicorn.run(
        "glassdome.server:app",
        host=host,
        port=port,
        reload=reload
    )


@main.command()
@click.option('--skip-admin', is_flag=True, help='Skip admin user creation')
def init(skip_admin):
    """Initialize Glassdome (database, config, etc.)"""
    click.echo("Initializing Glassdome...")
    click.echo(f"Database: {settings.database_url}")
    click.echo(f"Redis: {settings.redis_url}")
    
    async def do_init():
        from glassdome.core.database import init_db, AsyncSessionLocal
        from glassdome.auth.service import create_initial_admin
        
        # Initialize database tables
        click.echo("\n📦 Initializing database...")
        await init_db()
        click.echo("   ✓ Database tables created")
        
        # Create default admin user
        if not skip_admin:
            click.echo("\n👤 Checking admin user...")
            async with AsyncSessionLocal() as session:
                admin = await create_initial_admin(session)
                if admin:
                    click.echo(f"   ✓ Admin user created: {admin.username}")
                    click.echo(f"     Default password: changeme123!")
                else:
                    click.echo("   ✓ Admin user already exists")
        
        # Verify platform connections
        click.echo("\n🔌 Testing platform connections...")
        from glassdome.platforms.proxmox_client import get_proxmox_client
        try:
            client = get_proxmox_client("01")
            if await client.test_connection():
                click.echo("   ✓ Proxmox connected")
            else:
                click.echo("   ⚠ Proxmox not responding")
        except Exception as e:
            click.echo(f"   ⚠ Proxmox: {e}")
    
    asyncio.run(do_init())
    click.echo("\n✅ Glassdome initialized successfully")


@main.command()
def status():
    """Check Glassdome system status"""
    click.echo(f"═══════════════════════════════════════════")
    click.echo(f"  Glassdome v{__version__}")
    click.echo(f"═══════════════════════════════════════════")
    click.echo(f"Environment: {settings.environment}")
    
    async def do_status():
        # Check agent manager status
        click.echo("\n📊 Agent Manager:")
        try:
            from glassdome.agents.manager import agent_manager
            status = agent_manager.get_status()
            click.echo(f"   Agents: {status['total_agents']}")
            click.echo(f"   Queue: {status['queue_size']}")
            click.echo(f"   Running: {status['running']}")
        except Exception as e:
            click.echo(f"   ⚠ Error: {e}")
        
        # Check platform connectivity
        click.echo("\n🔌 Platforms:")
        platforms_status = []
        
        # Proxmox
        try:
            from glassdome.platforms.proxmox_client import get_proxmox_client
            client = get_proxmox_client("01")
            if await client.test_connection():
                platforms_status.append(("Proxmox", "✓ Connected"))
            else:
                platforms_status.append(("Proxmox", "✗ Not responding"))
        except Exception as e:
            platforms_status.append(("Proxmox", f"✗ {str(e)[:30]}"))
        
        # ESXi
        try:
            if settings.esxi_host:
                from glassdome.platforms.esxi_client import ESXiClient
                client = ESXiClient(settings.esxi_host, settings.esxi_user, settings.esxi_password)
                if await client.test_connection():
                    platforms_status.append(("ESXi", "✓ Connected"))
                else:
                    platforms_status.append(("ESXi", "✗ Not responding"))
            else:
                platforms_status.append(("ESXi", "⚠ Not configured"))
        except Exception as e:
            platforms_status.append(("ESXi", f"✗ {str(e)[:30]}"))
        
        # AWS
        try:
            if settings.aws_access_key_id:
                platforms_status.append(("AWS", "✓ Configured"))
            else:
                platforms_status.append(("AWS", "⚠ Not configured"))
        except Exception as e:
            platforms_status.append(("AWS", f"✗ {str(e)[:30]}"))
        
        # Azure
        try:
            if settings.azure_subscription_id:
                platforms_status.append(("Azure", "✓ Configured"))
            else:
                platforms_status.append(("Azure", "⚠ Not configured"))
        except Exception as e:
            platforms_status.append(("Azure", f"✗ {str(e)[:30]}"))
        
        for name, stat in platforms_status:
            click.echo(f"   {name}: {stat}")
        
        # Show active deployments
        click.echo("\n🚀 Active Deployments:")
        try:
            from sqlalchemy import select, func
            from glassdome.core.database import AsyncSessionLocal
            from glassdome.models.lab import Lab
            from glassdome.models.deployment import DeployedVM
            
            async with AsyncSessionLocal() as session:
                # Count labs
                lab_count = await session.execute(select(func.count(Lab.id)))
                labs = lab_count.scalar() or 0
                
                # Count deployed VMs
                vm_count = await session.execute(select(func.count(DeployedVM.id)))
                vms = vm_count.scalar() or 0
                
                click.echo(f"   Labs: {labs}")
                click.echo(f"   Deployed VMs: {vms}")
        except Exception as e:
            click.echo(f"   ⚠ Database: {e}")
    
    asyncio.run(do_status())


@main.command()
@click.option('--platform', type=click.Choice(['proxmox', 'azure', 'aws']), required=True)
def test_platform(platform):
    """Test platform connectivity"""
    click.echo(f"Testing {platform} connection...")
    
    # Use session-aware settings for secrets
    from glassdome.core.security import ensure_security_context, get_secure_settings
    try:
        ensure_security_context()
        secure_settings = get_secure_settings()
    except RuntimeError as e:
        click.echo(f"Error: {e}")
        click.echo("Run './glassdome_start' first to initialize the session.")
        return
    
    if platform == 'proxmox':
        from glassdome.platforms.proxmox_client import ProxmoxClient
        if not secure_settings.proxmox_host:
            click.echo("Error: Proxmox not configured")
            return
        
        client = ProxmoxClient(
            host=secure_settings.proxmox_host,
            user=secure_settings.proxmox_user,
            password=secure_settings.proxmox_password,
            verify_ssl=secure_settings.proxmox_verify_ssl
        )
        result = asyncio.run(client.test_connection())
        
    elif platform == 'azure':
        from glassdome.platforms.azure_client import AzureClient
        if not secure_settings.azure_subscription_id:
            click.echo("Error: Azure not configured")
            return
        
        client = AzureClient(
            subscription_id=secure_settings.azure_subscription_id,
            tenant_id=secure_settings.azure_tenant_id,
            client_id=secure_settings.azure_client_id,
            client_secret=secure_settings.azure_client_secret
        )
        result = asyncio.run(client.test_connection())
        
    elif platform == 'aws':
        from glassdome.platforms.aws_client import AWSClient
        if not secure_settings.aws_access_key_id:
            click.echo("Error: AWS not configured")
            return
        
        client = AWSClient(
            access_key_id=secure_settings.aws_access_key_id,
            secret_access_key=secure_settings.aws_secret_access_key,
            region=secure_settings.aws_region
        )
        result = asyncio.run(client.test_connection())
    
    if result:
        click.echo(f"✓ {platform} connection successful")
    else:
        click.echo(f"✗ {platform} connection failed")


@main.group()
def agent():
    """Agent management commands"""
    pass


@agent.command('list')
def agent_list():
    """List all registered agents"""
    from glassdome.agents.manager import agent_manager
    status = agent_manager.get_status()
    
    click.echo(f"Total Agents: {status['total_agents']}")
    click.echo(f"Queue Size: {status['queue_size']}")
    click.echo(f"Running: {status['running']}")
    click.echo("\nAgents:")
    
    for agent_id, info in status['agents'].items():
        click.echo(f"  {agent_id}: {info['type']} - {info['status']}")


@agent.command('start')
def agent_start():
    """Start the agent manager"""
    from glassdome.agents.manager import agent_manager
    click.echo("Starting agent manager...")
    asyncio.run(agent_manager.start())


@main.group()
def lab():
    """Lab management commands"""
    pass


@lab.command('list')
@click.option('--format', 'fmt', type=click.Choice(['table', 'json']), default='table', help='Output format')
def lab_list(fmt):
    """List all labs"""
    async def do_list():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.models.lab import Lab
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Lab).order_by(Lab.created_at.desc()))
            labs = result.scalars().all()
            
            if not labs:
                click.echo("No labs found.")
                return
            
            if fmt == 'json':
                import json
                data = [{"id": lab.id, "name": lab.name, "status": lab.status} for lab in labs]
                click.echo(json.dumps(data, indent=2))
            else:
                click.echo(f'\n{"ID":<40} {"Name":<30} {"Status":<12} {"VMs":<6}')
                click.echo('─' * 90)
                
                for lab in labs:
                    vm_count = len(lab.elements) if hasattr(lab, 'elements') and lab.elements else 0
                    click.echo(f'{lab.id:<40} {(lab.name or "Unnamed"):<30} {(lab.status or "draft"):<12} {vm_count:<6}')
                
                click.echo(f'\nTotal: {len(labs)} labs')
    
    asyncio.run(do_list())


@lab.command('create')
@click.option('--name', required=True, help='Lab name')
@click.option('--description', default='', help='Lab description')
@click.option('--template', help='Template ID to use')
def lab_create(name, description, template):
    """Create a new lab"""
    async def do_create():
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.models.lab import Lab
        import uuid
        
        async with AsyncSessionLocal() as session:
            lab_id = f"lab-{uuid.uuid4().hex[:8]}"
            
            lab = Lab(
                id=lab_id,
                name=name,
                description=description,
                status="draft",
                elements=[]
            )
            session.add(lab)
            await session.commit()
            
            click.echo(f"✅ Lab created successfully!")
            click.echo(f"   ID: {lab_id}")
            click.echo(f"   Name: {name}")
            
            if template:
                click.echo(f"   Template: {template} (template cloning not yet implemented)")
    
    asyncio.run(do_create())


@lab.command('show')
@click.argument('lab_id')
def lab_show(lab_id):
    """Show details of a specific lab"""
    async def do_show():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.models.lab import Lab
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Lab).where(Lab.id == lab_id))
            lab = result.scalar_one_or_none()
            
            if not lab:
                click.echo(f"❌ Lab not found: {lab_id}")
                return
            
            click.echo(f"\n{'═' * 50}")
            click.echo(f"Lab: {lab.name or 'Unnamed'}")
            click.echo(f"{'═' * 50}")
            click.echo(f"ID:          {lab.id}")
            click.echo(f"Status:      {lab.status or 'draft'}")
            click.echo(f"Description: {lab.description or 'No description'}")
            click.echo(f"Created:     {lab.created_at}")
            
            if hasattr(lab, 'elements') and lab.elements:
                click.echo(f"\nElements ({len(lab.elements)}):")
                for elem in lab.elements:
                    click.echo(f"  - {elem.get('name', 'Unnamed')}: {elem.get('type', 'unknown')}")
    
    asyncio.run(do_show())


@lab.command('delete')
@click.argument('lab_id')
@click.confirmation_option(prompt='Are you sure you want to delete this lab?')
def lab_delete(lab_id):
    """Delete a lab"""
    async def do_delete():
        from sqlalchemy import select, delete
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.models.lab import Lab
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Lab).where(Lab.id == lab_id))
            lab = result.scalar_one_or_none()
            
            if not lab:
                click.echo(f"❌ Lab not found: {lab_id}")
                return
            
            await session.execute(delete(Lab).where(Lab.id == lab_id))
            await session.commit()
            click.echo(f"✅ Lab deleted: {lab_id}")
    
    asyncio.run(do_delete())


@main.group()
def deploy():
    """Deployment management commands"""
    pass


@deploy.command('list')
@click.option('--format', 'fmt', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.option('--lab-id', help='Filter by lab ID')
def deploy_list(fmt, lab_id):
    """List all deployments"""
    async def do_list():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.models.deployment import DeployedVM
        
        async with AsyncSessionLocal() as session:
            query = select(DeployedVM).order_by(DeployedVM.created_at.desc())
            if lab_id:
                query = query.where(DeployedVM.lab_id == lab_id)
            
            result = await session.execute(query)
            vms = result.scalars().all()
            
            if not vms:
                click.echo("No deployments found.")
                return
            
            if fmt == 'json':
                import json
                data = [{
                    "id": vm.id,
                    "lab_id": vm.lab_id,
                    "name": vm.name,
                    "vm_id": vm.vm_id,
                    "platform": vm.platform,
                    "status": vm.status,
                    "ip_address": vm.ip_address
                } for vm in vms]
                click.echo(json.dumps(data, indent=2))
            else:
                click.echo(f'\n{"ID":<6} {"Lab ID":<15} {"Name":<20} {"Platform":<10} {"Status":<12} {"IP":<15}')
                click.echo('─' * 85)
                
                for vm in vms:
                    click.echo(
                        f'{vm.id:<6} {(vm.lab_id or "")[:15]:<15} {(vm.name or "")[:20]:<20} '
                        f'{(vm.platform or ""):<10} {(vm.status or ""):<12} {(vm.ip_address or ""):<15}'
                    )
                
                click.echo(f'\nTotal: {len(vms)} deployed VMs')
    
    asyncio.run(do_list())


@deploy.command('create')
@click.option('--lab-id', required=True, help='Lab ID to deploy')
@click.option('--platform', type=click.Choice(['proxmox', 'esxi', 'azure', 'aws']), default='proxmox', help='Target platform')
@click.option('--instance', default='01', help='Platform instance ID (for multi-cluster)')
def deploy_create(lab_id, platform, instance):
    """Deploy a lab to a platform"""
    async def do_deploy():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.models.lab import Lab
        
        async with AsyncSessionLocal() as session:
            # Verify lab exists
            result = await session.execute(select(Lab).where(Lab.id == lab_id))
            lab = result.scalar_one_or_none()
            
            if not lab:
                click.echo(f"❌ Lab not found: {lab_id}")
                return
            
            click.echo(f"🚀 Deploying lab '{lab.name}' to {platform}...")
            click.echo(f"   Lab ID: {lab_id}")
            click.echo(f"   Platform: {platform} (instance: {instance})")
            
            # Check if lab has elements to deploy
            if not lab.elements:
                click.echo("⚠️  Lab has no elements to deploy.")
                click.echo("   Add VMs to the lab via the web UI first.")
                return
            
            click.echo(f"   Elements: {len(lab.elements)} VMs")
            
            # For now, queue the deployment (actual deployment via API/workers)
            click.echo("\n📋 Deployment queued.")
            click.echo("   Use 'glassdome deploy list' to check status.")
            click.echo("   Or monitor via the web UI at http://localhost:8011")
            
            # Update lab status
            lab.status = "deploying"
            await session.commit()
    
    asyncio.run(do_deploy())


@deploy.command('destroy')
@click.argument('deployment_id')
@click.option('--force', is_flag=True, help='Force destroy without confirmation')
def deploy_destroy(deployment_id, force):
    """Destroy a deployment (by VM ID or lab ID)"""
    if not force:
        if not click.confirm(f'Destroy deployment {deployment_id}?'):
            return
    
    async def do_destroy():
        from sqlalchemy import select, delete
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.models.deployment import DeployedVM
        
        async with AsyncSessionLocal() as session:
            # Try to find by ID first
            result = await session.execute(
                select(DeployedVM).where(
                    (DeployedVM.id == int(deployment_id) if deployment_id.isdigit() else False) |
                    (DeployedVM.lab_id == deployment_id)
                )
            )
            vms = result.scalars().all()
            
            if not vms:
                click.echo(f"❌ No deployments found for: {deployment_id}")
                return
            
            click.echo(f"🗑️  Destroying {len(vms)} VM(s)...")
            
            for vm in vms:
                click.echo(f"   Destroying: {vm.name} ({vm.platform}:{vm.vm_id})")
                
                # Attempt to stop/delete VM on platform
                try:
                    if vm.platform == 'proxmox':
                        from glassdome.platforms.proxmox_client import get_proxmox_client
                        client = get_proxmox_client(vm.platform_instance or "01")
                        await client.stop_vm(str(vm.vm_id))
                        await client.delete_vm(str(vm.vm_id))
                        click.echo(f"   ✓ VM {vm.vm_id} deleted from Proxmox")
                except Exception as e:
                    click.echo(f"   ⚠ Platform cleanup failed: {e}")
                
                # Remove from database
                await session.delete(vm)
            
            await session.commit()
            click.echo(f"✅ Deployment destroyed")
    
    asyncio.run(do_destroy())


@deploy.command('status')
@click.argument('lab_id')
def deploy_status(lab_id):
    """Check deployment status for a lab"""
    async def do_status():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.models.lab import Lab
        from glassdome.models.deployment import DeployedVM
        
        async with AsyncSessionLocal() as session:
            # Get lab
            result = await session.execute(select(Lab).where(Lab.id == lab_id))
            lab = result.scalar_one_or_none()
            
            if not lab:
                click.echo(f"❌ Lab not found: {lab_id}")
                return
            
            # Get deployed VMs
            result = await session.execute(
                select(DeployedVM).where(DeployedVM.lab_id == lab_id)
            )
            vms = result.scalars().all()
            
            click.echo(f"\n{'═' * 60}")
            click.echo(f"Deployment Status: {lab.name}")
            click.echo(f"{'═' * 60}")
            click.echo(f"Lab ID: {lab_id}")
            click.echo(f"Status: {lab.status or 'unknown'}")
            click.echo(f"Deployed VMs: {len(vms)}")
            
            if vms:
                click.echo(f"\n{'Name':<25} {'Status':<12} {'IP':<15} {'Platform':<10}")
                click.echo('─' * 65)
                for vm in vms:
                    click.echo(
                        f'{(vm.name or "")[:25]:<25} {(vm.status or ""):<12} '
                        f'{(vm.ip_address or "pending"):<15} {(vm.platform or ""):<10}'
                    )
            
            # Calculate progress
            if lab.elements:
                total = len(lab.elements)
                deployed = len([v for v in vms if v.status == 'running'])
                progress = (deployed / total) * 100 if total > 0 else 0
                click.echo(f"\nProgress: {deployed}/{total} VMs ({progress:.0f}%)")
    
    asyncio.run(do_status())


@main.group()
def secrets():
    """Secrets management commands"""
    pass


@secrets.command('set')
@click.argument('key')
@click.option('--value', prompt=True, hide_input=True, help='Secret value (prompted if not provided)')
def secrets_set(key, value):
    """Set a secret value"""
    try:
        secrets = get_secrets_manager()
        if secrets.set_secret(key, value):
            click.echo(f"✅ Secret '{key}' stored successfully")
        else:
            click.echo(f"❌ Failed to store secret '{key}'")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@secrets.command('get')
@click.argument('key')
def secrets_get(key):
    """Get a secret value (displayed, use with caution)"""
    try:
        secrets = get_secrets_manager()
        value = secrets.get_secret(key)
        if value:
            click.echo(f"Value for '{key}': {value}")
        else:
            click.echo(f"❌ Secret '{key}' not found")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@secrets.command('list')
def secrets_list():
    """List all stored secret keys"""
    try:
        secrets = get_secrets_manager()
        keys = secrets.list_secrets()
        if keys:
            click.echo("Stored secrets:")
            for key in keys:
                click.echo(f"  • {key}")
        else:
            click.echo("No secrets stored")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@secrets.command('delete')
@click.argument('key')
@click.confirmation_option(prompt='Are you sure you want to delete this secret?')
def secrets_delete(key):
    """Delete a secret"""
    try:
        secrets = get_secrets_manager()
        if secrets.delete_secret(key):
            click.echo(f"✅ Secret '{key}' deleted")
        else:
            click.echo(f"❌ Secret '{key}' not found or could not be deleted")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@secrets.command('migrate')
@click.option('--env-file', type=click.Path(exists=True), default='.env', help='Path to .env file')
def secrets_migrate(env_file):
    """Migrate secrets from .env file to secure store"""
    from glassdome.core.secrets import get_secrets_manager
    
    env_path = Path(env_file)
    if not env_path.exists():
        click.echo(f"❌ .env file not found: {env_path}")
        return
    
    click.echo(f"📄 Migrating secrets from {env_path}")
    click.echo("⚠️  This will prompt for a master password if this is the first time.")
    
    try:
        secrets = get_secrets_manager()
        results = secrets.migrate_from_env(env_path)
        
        if not results:
            click.echo("⚠️  No secrets found to migrate")
            return
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        click.echo(f"\n✅ Migrated {success_count}/{total_count} secrets:")
        for secret_key, success in sorted(results.items()):
            status = "✅" if success else "❌"
            click.echo(f"  {status} {secret_key}")
        
        if success_count == total_count:
            click.echo("\n✅ Migration complete!")
    except Exception as e:
        click.echo(f"❌ Migration failed: {e}")


# =============================================================================
# AUTH COMMANDS - User and Password Management
# =============================================================================

@main.group()
def auth():
    """Authentication and user management commands"""
    pass


@auth.command('reset-password')
@click.option('--username', '-u', required=True, help='Username to reset')
@click.option('--password', '-p', help='New password (will prompt if not provided)')
def auth_reset_password(username, password):
    """
    Reset a user's password.
    
    Use this when a user is locked out or forgot their password.
    
    Examples:
        glassdome auth reset-password -u admin
        glassdome auth reset-password -u john -p newpassword123
    """
    if not password:
        password = getpass.getpass('Enter new password: ')
        confirm = getpass.getpass('Confirm password: ')
        if password != confirm:
            click.echo('❌ Passwords do not match')
            return
    
    if len(password) < 8:
        click.echo('❌ Password must be at least 8 characters')
        return
    
    async def do_reset():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.auth.models import User
        from glassdome.auth.service import get_password_hash
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                click.echo(f'❌ User not found: {username}')
                return False
            
            user.hashed_password = get_password_hash(password)
            user.is_active = True  # Also reactivate if deactivated
            await session.commit()
            
            click.echo(f'✅ Password reset for user: {username}')
            return True
    
    asyncio.run(do_reset())


@auth.command('create-admin')
@click.option('--email', '-e', default='admin@glassdome.local', help='Admin email')
@click.option('--username', '-u', default='admin', help='Admin username')
@click.option('--password', '-p', help='Admin password (will prompt if not provided)')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing admin user')
def auth_create_admin(email, username, password, force):
    """
    Create or reset the admin user.
    
    Use this for initial setup or emergency admin recovery.
    
    Examples:
        glassdome auth create-admin
        glassdome auth create-admin -u superadmin -e super@company.com
        glassdome auth create-admin --force  # Reset existing admin
    """
    if not password:
        password = getpass.getpass('Enter admin password: ')
        confirm = getpass.getpass('Confirm password: ')
        if password != confirm:
            click.echo('❌ Passwords do not match')
            return
    
    if len(password) < 8:
        click.echo('❌ Password must be at least 8 characters')
        return
    
    async def do_create():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.auth.models import User, UserRole
        from glassdome.auth.service import get_password_hash
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                if not force:
                    click.echo(f'❌ User already exists: {username}')
                    click.echo(f'   Use --force to reset this user to admin')
                    return False
                
                existing.email = email
                existing.hashed_password = get_password_hash(password)
                existing.role = UserRole.ADMIN.value
                existing.level = 100
                existing.is_active = True
                await session.commit()
                click.echo(f'✅ Existing user reset to admin: {username}')
            else:
                admin = User(
                    email=email,
                    username=username,
                    hashed_password=get_password_hash(password),
                    role=UserRole.ADMIN.value,
                    level=100,
                    is_active=True,
                )
                session.add(admin)
                await session.commit()
                click.echo(f'✅ Admin user created: {username}')
            
            click.echo(f'   Email: {email}')
            click.echo(f'   Role: admin (level 100)')
            return True
    
    asyncio.run(do_create())


@auth.command('list-users')
def auth_list_users():
    """
    List all users in the system.
    
    Example:
        glassdome auth list-users
    """
    async def do_list():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.auth.models import User
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).order_by(User.id))
            users = result.scalars().all()
            
            if not users:
                click.echo('No users found.')
                return
            
            click.echo(f'\n{"ID":<5} {"Username":<20} {"Email":<30} {"Role":<12} {"Level":<6} {"Active":<8}')
            click.echo('─' * 85)
            
            for user in users:
                active = '✓' if user.is_active else '✗'
                click.echo(
                    f'{user.id:<5} {user.username:<20} {user.email:<30} '
                    f'{user.role:<12} {user.level:<6} {active:<8}'
                )
            
            click.echo(f'\nTotal: {len(users)} users')
    
    asyncio.run(do_list())


@auth.command('emergency-reset')
def auth_emergency_reset():
    """
    Emergency admin reset - creates 'emergency_admin' account.
    
    Use this when completely locked out of the system.
    Creates a temporary admin account with a random password.
    
    Example:
        glassdome auth emergency-reset
    """
    import secrets as token_secrets
    
    password = token_secrets.token_urlsafe(16)
    
    async def do_emergency():
        from sqlalchemy import select
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.auth.models import User, UserRole
        from glassdome.auth.service import get_password_hash
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.username == 'emergency_admin')
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.hashed_password = get_password_hash(password)
                existing.is_active = True
                await session.commit()
                click.echo('🔓 Emergency admin account reset!')
            else:
                admin = User(
                    email='emergency@glassdome.local',
                    username='emergency_admin',
                    hashed_password=get_password_hash(password),
                    role=UserRole.ADMIN.value,
                    level=100,
                    is_active=True,
                )
                session.add(admin)
                await session.commit()
                click.echo('🔓 Emergency admin account created!')
            
            click.echo('')
            click.echo('╔══════════════════════════════════════════════════════╗')
            click.echo('║  EMERGENCY ADMIN CREDENTIALS                         ║')
            click.echo('╠══════════════════════════════════════════════════════╣')
            click.echo(f'║  Username: emergency_admin                           ║')
            click.echo(f'║  Password: {password:<40} ║')
            click.echo('╠══════════════════════════════════════════════════════╣')
            click.echo('║  ⚠️  CHANGE THIS PASSWORD IMMEDIATELY                 ║')
            click.echo('║  ⚠️  DELETE THIS ACCOUNT AFTER RECOVERY               ║')
            click.echo('╚══════════════════════════════════════════════════════╝')
    
    asyncio.run(do_emergency())


if __name__ == '__main__':
    main()

