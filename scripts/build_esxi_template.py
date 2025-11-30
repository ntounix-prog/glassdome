#!/usr/bin/env python3
"""
ESXi Template Builder CLI

Usage:
    python scripts/build_esxi_template.py --name ubuntu-2204-template
    python scripts/build_esxi_template.py --name ubuntu-2404-template --version 24.04
    
Environment Variables (from .env):
    ESXI_HOST
    ESXI_USER
    ESXI_PASSWORD
    ESXI_DATASTORE
    ESXI_NETWORK
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()

from glassdome.platforms.esxi_template_builder import ESXiTemplateBuilder

# Use centralized logging
from glassdome.core.logging import setup_logging_from_settings
setup_logging_from_settings()
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Build ESXi-compatible Ubuntu cloud-init template'
    )
    parser.add_argument(
        '--name',
        default='ubuntu-2204-glassdome',
        help='Template name (default: ubuntu-2204-glassdome)'
    )
    parser.add_argument(
        '--version',
        default='22.04',
        help='Ubuntu version (default: 22.04)'
    )
    parser.add_argument(
        '--username',
        default='ubuntu',
        help='Default username (default: ubuntu)'
    )
    parser.add_argument(
        '--password',
        default='glassdome123',
        help='Default password (default: glassdome123)'
    )
    parser.add_argument(
        '--ssh-key',
        action='append',
        help='SSH public key (can be specified multiple times)'
    )
    
    args = parser.parse_args()
    
    # Validate settings
    if not settings.esxi_host:
        logger.error("ESXI_HOST not configured in .env")
        sys.exit(1)
    
    if not settings.esxi_user or not settings.esxi_password:
        logger.error("ESXI_USER and ESXI_PASSWORD required in .env")
        sys.exit(1)
    
    if not settings.esxi_datastore:
        logger.error("ESXI_DATASTORE not configured in .env")
        sys.exit(1)
    
    logger.info("="*60)
    logger.info("  ESXi Template Builder")
    logger.info("="*60)
    logger.info(f"ESXi Host: {settings.esxi_host}")
    logger.info(f"Datastore: {settings.esxi_datastore}")
    logger.info(f"Network: {settings.esxi_network}")
    logger.info(f"Template: {args.name}")
    logger.info(f"Ubuntu: {args.version}")
    logger.info(f"Username: {args.username}")
    logger.info("="*60)
    
    # Build template
    builder = ESXiTemplateBuilder(
        esxi_host=settings.esxi_host,
        esxi_user=settings.esxi_user,
        esxi_password=settings.esxi_password,
        datastore=settings.esxi_datastore,
        network=settings.esxi_network,
        verify_ssl=settings.esxi_verify_ssl
    )
    
    try:
        result = builder.build_template(
            template_name=args.name,
            ubuntu_version=args.version,
            username=args.username,
            password=args.password,
            ssh_keys=args.ssh_key
        )
        
        logger.info("\n" + "="*60)
        logger.info("  ✅ TEMPLATE BUILD COMPLETE!")
        logger.info("="*60)
        logger.info(f"Template Name: {result['template_name']}")
        logger.info(f"VMDK Path: {result['vmdk_path']}")
        logger.info(f"ISO Path: {result['iso_path']}")
        logger.info(f"Username: {result['username']}")
        logger.info(f"Password: {result['password']}")
        logger.info("="*60)
        logger.info("\nNext Steps:")
        logger.info("1. Test the template by creating a VM")
        logger.info("2. Update ESXI_UBUNTU_TEMPLATE in .env")
        logger.info(f"   ESXI_UBUNTU_TEMPLATE={result['template_name']}")
        logger.info("3. Use in Glassdome deployments")
        
    except Exception as e:
        logger.error(f"❌ Template build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

