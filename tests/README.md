# Tests Directory

**Purpose:** Automated test suite for Glassdome components.

---

## Structure

```
tests/
├── unit/               # Unit tests for individual components
│   ├── agents/
│   ├── platforms/
│   └── research/
├── integration/        # Integration tests
│   ├── proxmox/
│   ├── agents/
│   └── orchestration/
├── e2e/               # End-to-end tests
│   ├── deployment/
│   └── research/
└── fixtures/          # Test fixtures and mocks
```

---

## Running Tests

### All Tests
```bash
pytest
```

### Specific Category
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Specific Module
```bash
pytest tests/unit/agents/test_ubuntu_agent.py
```

### With Coverage
```bash
pytest --cov=glassdome --cov-report=html
```

---

## Test Categories

### Unit Tests (`unit/`)
Fast, isolated tests for individual functions/classes:
- No external dependencies
- Mock all external services
- Test business logic

### Integration Tests (`integration/`)
Tests for component integration:
- May connect to real services (in test mode)
- Test API contracts
- Test agent coordination

### End-to-End Tests (`e2e/`)
Full workflow tests:
- Deploy actual VMs (in test environment)
- Test complete pipelines
- Verify end-user scenarios

---

## Writing Tests

### Naming Convention
```python
# File: test_[module_name].py
# Class: Test[ClassName]
# Method: test_[what_it_does]

# Example:
# tests/unit/agents/test_ubuntu_agent.py
class TestUbuntuAgent:
    def test_creates_vm_with_correct_config(self):
        pass
    
    def test_handles_missing_template_error(self):
        pass
```

### Test Structure
```python
# Arrange - Set up test data
agent = UbuntuAgent()
config = {"memory": 2048, "cores": 2}

# Act - Execute the code being tested
result = agent.create_vm(config)

# Assert - Verify the result
assert result["status"] == "success"
assert result["vm_id"] is not None
```

---

## Fixtures

Common test fixtures in `conftest.py`:
- `mock_proxmox_client`
- `mock_llm_client`
- `sample_cve_data`
- `test_config`

---

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Main branch commits
- Nightly builds

---

*Test-driven development for reliability*

