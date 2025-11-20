# Tools Scripts

This directory contains utility and verification scripts for Glassdome.

## Available Tools

### `verify_iac_tools.py`
Comprehensive verification of Ansible and Terraform installations.

**Usage:**
```bash
python scripts/tools/verify_iac_tools.py
```

**What it checks:**
- ✅ Ansible CLI and Python package
- ✅ Terraform CLI and Python package
- ✅ Required directory structure
- ✅ Can execute Ansible modules
- ✅ Can initialize Terraform configs

**Output:**
- Detailed verification report
- Pass/fail status for each check
- Troubleshooting tips if failures occur

---

## Adding New Tools

When adding new tool scripts:

1. **Place in this directory:** `scripts/tools/`
2. **Make executable:** `chmod +x script_name.py`
3. **Add shebang:** `#!/usr/bin/env python3`
4. **Document here:** Update this README
5. **Use PROJECT_ROOT:**
   ```python
   PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
   ```

---

## Purpose

Tool scripts are for:
- **Verification:** Check installations and configurations
- **Diagnostics:** Identify issues and provide troubleshooting
- **Utilities:** Helper tools for development and operations

**Not for:**
- Deployment scripts (use `scripts/deployment/`)
- Setup scripts (use `scripts/setup/`)
- Tests (use `tests/`)

