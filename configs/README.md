# Configs Directory

**Purpose:** Configuration templates and examples for various deployment scenarios.

---

## Structure

```
configs/
├── templates/          # Lab templates
│   ├── web_security.yaml
│   ├── network_defense.yaml
│   └── ctf_lab.yaml
├── scenarios/          # Training scenarios
├── platforms/          # Platform-specific configs
└── examples/           # Example configurations
```

---

## Lab Templates (`templates/`)

Pre-built lab configurations for common training scenarios:

```yaml
# web_security.yaml
name: "Web Security Training Lab"
description: "Complete web app security lab with vulnerabilities"
vms:
  - name: "web-server"
    os: "ubuntu-22.04"
    memory: 2048
    cores: 2
    vulnerabilities:
      - sql_injection_basic
      - xss_reflected
      - command_injection
    packages:
      - apache2
      - php
      - mysql-server
```

---

## Scenarios (`scenarios/`)

Complete training scenario definitions including:
- VM configurations
- Network topology
- Learning objectives
- Student instructions
- Answer keys

---

## Platform Configs (`platforms/`)

Platform-specific configuration examples:
- Proxmox network configurations
- Azure resource group templates
- AWS CloudFormation templates

---

## Using Templates

### Via CLI (Future)
```bash
glassdome lab create --template web_security
```

### Programmatically
```python
from glassdome.orchestration import LabOrchestrator
import yaml

with open("configs/templates/web_security.yaml") as f:
    template = yaml.safe_load(f)

orchestrator = LabOrchestrator()
lab = orchestrator.deploy_from_template(template)
```

### Via API
```bash
curl -X POST http://localhost:8001/api/v1/labs/from-template \
  -H "Content-Type: application/json" \
  -d '{"template": "web_security"}'
```

---

*Reusable configurations for rapid deployment*

