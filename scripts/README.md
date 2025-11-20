# Scripts Directory

**Purpose:** All utility scripts, organized by function.

---

## Directory Structure

```
scripts/
├── setup/          # Setup and configuration scripts
├── testing/        # Testing and validation scripts
├── deployment/     # Deployment automation scripts
└── tools/          # Utility tools and helpers
```

---

## Setup Scripts (`setup/`)

Scripts for initial system setup and configuration:

- **`setup.sh`** - Create and configure Python virtual environment
- **`setup_proxmox.py`** - Interactive Proxmox connection configuration
- **`install_iac_tools.sh`** - Install Ansible and Terraform

**Usage:**
```bash
# First time setup
./scripts/setup/setup.sh

# Configure Proxmox
python scripts/setup/setup_proxmox.py

# Install IaC tools
bash scripts/setup/install_iac_tools.sh
```

---

## Testing Scripts (`testing/`)

Scripts for testing components and infrastructure:

- **`test_vm_creation.py`** - Test VM creation on Proxmox
- **`monitor_infrastructure.py`** - Test Overseer Agent monitoring

**Usage:**
```bash
# Test VM deployment
python scripts/testing/test_vm_creation.py

# Test monitoring
python scripts/testing/monitor_infrastructure.py
```

---

## Deployment Scripts (`deployment/`)

Scripts for automated deployment tasks:

- **`create_template_auto.py`** - Automatically create Proxmox cloud-init templates

**Usage:**
```bash
# Create Ubuntu 22.04 template
python scripts/deployment/create_template_auto.py
```

---

## Tools (`tools/`)

General-purpose utility and verification scripts:

- **`verify_iac_tools.py`** - Verify Ansible and Terraform installation

**Usage:**
```bash
# Verify IaC tools installation
python scripts/tools/verify_iac_tools.py
```

---

## Guidelines

### Adding New Scripts

1. **Determine Category:**
   - Setup: Initial configuration, one-time setup
   - Testing: Validation, testing, debugging
   - Deployment: Automation, provisioning
   - Tools: General utilities

2. **Place in Correct Directory:**
   ```bash
   scripts/
   └── [category]/
       └── your_script.py
   ```

3. **Add to This README:**
   - Add to appropriate section
   - Include brief description
   - Show usage example

4. **Make Executable (if shell script):**
   ```bash
   chmod +x scripts/category/your_script.sh
   ```

### Script Standards

- **Naming:** Use snake_case for Python, kebab-case for shell scripts
- **Shebang:** Include `#!/usr/bin/env python3` or `#!/bin/bash`
- **Documentation:** Add docstring or header comment explaining purpose
- **Error Handling:** Handle errors gracefully with helpful messages
- **Environment:** Don't assume CWD, use absolute paths or change to project root

---

## Running Scripts

### From Project Root

```bash
# Python scripts
python scripts/setup/setup_proxmox.py

# Shell scripts
./scripts/setup/setup.sh
# or
bash scripts/setup/setup.sh
```

### From Scripts Directory

```bash
cd scripts/testing
python test_vm_creation.py
```

### As Glassdome CLI Commands (Future)

```bash
# These scripts might become CLI commands:
glassdome setup proxmox     # → scripts/setup/setup_proxmox.py
glassdome test vm-creation  # → scripts/testing/test_vm_creation.py
glassdome deploy template   # → scripts/deployment/create_template_auto.py
```

---

## Script Dependencies

All scripts assume:
1. Virtual environment is activated (`source venv/bin/activate`)
2. `glassdome` package is installed (`pip install -e .`)
3. `.env` file is configured (copy from `env.example`)
4. API keys are available (in `~/.bashrc` or `.env`)

---

*Organized for clarity and maintainability*

