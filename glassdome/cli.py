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
def init():
    """Initialize Glassdome (database, config, etc.)"""
    click.echo("Initializing Glassdome...")
    
    # Check database connection
    click.echo(f"Database: {settings.database_url}")
    click.echo(f"Redis: {settings.redis_url}")
    
    # TODO: Run database migrations
    # TODO: Create default admin user
    # TODO: Verify platform connections
    
    click.echo("✓ Glassdome initialized successfully")


@main.command()
def status():
    """Check Glassdome system status"""
    click.echo(f"Glassdome v{__version__}")
    click.echo(f"Environment: {settings.environment}")
    click.echo(f"Database: {settings.database_url}")
    click.echo(f"Redis: {settings.redis_url}")
    
    # TODO: Check agent manager status
    # TODO: Check platform connectivity
    # TODO: Show active deployments


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
def lab_list():
    """List all labs"""
    click.echo("Labs:")
    # TODO: Query database and list labs


@lab.command('create')
@click.option('--name', required=True, help='Lab name')
@click.option('--template', help='Template to use')
def lab_create(name, template):
    """Create a new lab"""
    click.echo(f"Creating lab: {name}")
    # TODO: Create lab from template or blank


@main.group()
def deploy():
    """Deployment management commands"""
    pass


@deploy.command('list')
def deploy_list():
    """List all deployments"""
    click.echo("Deployments:")
    # TODO: Query database and list deployments


@deploy.command('create')
@click.option('--lab-id', required=True, help='Lab ID to deploy')
@click.option('--platform', type=click.Choice(['proxmox', 'azure', 'aws']), required=True)
def deploy_create(lab_id, platform):
    """Create a new deployment"""
    click.echo(f"Deploying lab {lab_id} to {platform}...")
    # TODO: Trigger deployment


@deploy.command('destroy')
@click.argument('deployment_id')
def deploy_destroy(deployment_id):
    """Destroy a deployment"""
    if click.confirm(f'Destroy deployment {deployment_id}?'):
        click.echo(f"Destroying deployment {deployment_id}...")
        # TODO: Destroy deployment


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

