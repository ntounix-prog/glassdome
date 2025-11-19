"""
Glassdome CLI - Command Line Interface
"""
import click
import asyncio
from glassdome import __version__
from glassdome.core.config import settings


@click.group()
@click.version_option(version=__version__)
def main():
    """Glassdome - Agentic Cyber Range Deployment Framework"""
    pass


@main.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8001, help='Port to bind to')
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
    
    if platform == 'proxmox':
        from glassdome.platforms.proxmox_client import ProxmoxClient
        if not settings.proxmox_host:
            click.echo("Error: Proxmox not configured")
            return
        
        client = ProxmoxClient(
            host=settings.proxmox_host,
            user=settings.proxmox_user,
            password=settings.proxmox_password,
            verify_ssl=settings.proxmox_verify_ssl
        )
        result = asyncio.run(client.test_connection())
        
    elif platform == 'azure':
        from glassdome.platforms.azure_client import AzureClient
        if not settings.azure_subscription_id:
            click.echo("Error: Azure not configured")
            return
        
        client = AzureClient(
            subscription_id=settings.azure_subscription_id,
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret
        )
        result = asyncio.run(client.test_connection())
        
    elif platform == 'aws':
        from glassdome.platforms.aws_client import AWSClient
        if not settings.aws_access_key_id:
            click.echo("Error: AWS not configured")
            return
        
        client = AWSClient(
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
            region=settings.aws_region
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


if __name__ == '__main__':
    main()

