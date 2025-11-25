# Security Considerations: Session Cache & OS Keyring

## Overview

Glassdome uses a session cache file and OS keyring to enable cross-process session sharing. This document outlines the security implications and attack vectors.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Process 1: ./glassdome_start                          │
│  - Prompts for master password                          │
│  - Decrypts master key                                 │
│  - Stores master key in OS keyring                      │
│  - Saves session cache (metadata only)                  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  OS Keyring (Linux Secret Service / macOS Keychain)    │
│  - Stores encrypted master key                         │
│  - OS-level encryption                                 │
│  - Accessible by same user if unlocked                  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Process 2: python script.py                            │
│  - Checks session cache (valid)                         │
│  - Gets master key from keyring (no password!)         │
│  - Loads secrets                                        │
└─────────────────────────────────────────────────────────┘
```

## Security Concerns

### 1. OS Keyring Access

**Risk Level: MEDIUM**

- **If keyring is unlocked** (user is logged in), any process running as the same user can access it
- **OS keyring encryption** is handled by the OS, but if unlocked, the key is accessible
- **Same-user processes** can read from keyring without additional authentication

**Attack Vector:**
```python
# Malicious script running as same user
import keyring
master_key = keyring.get_password("glassdome", "master_key")
# Now has access to decrypt all secrets!
```

**Mitigation:**
- Keyring is typically locked when user logs out
- Keyring unlock requires user authentication (usually)
- But if user is logged in, keyring may be unlocked

### 2. Session Cache File

**Risk Level: LOW**

- Cache file only contains **metadata** (timestamps, secret count)
- **No secrets or master key** stored in cache
- Protected with 600 permissions (user-only)
- But any process as same user can read it

**Attack Vector:**
```bash
# Attacker can check if session exists
cat ~/.glassdome/session_cache.json
# Knows: session is valid, when it expires
# But: doesn't have master key or secrets
```

**Mitigation:**
- File permissions (600) prevent other users from reading
- Only metadata, no actual secrets
- Expires after 8 hours

### 3. Process-Level Access

**Risk Level: HIGH (if keyring unlocked)**

If an attacker has:
- Access to run processes as the same user
- Keyring is unlocked (user logged in)

Then they can:
1. Read session cache → know session exists
2. Access keyring → get master key
3. Decrypt all secrets

**Attack Scenario:**
```python
# Attacker's malicious script
from glassdome.core.session import get_session
session = get_session()
session.initialize()  # Uses cache + keyring, no password!
# Now has access to all secrets
```

## Security Recommendations

### Current Protections

1. ✅ **Session cache only contains metadata** (no secrets)
2. ✅ **File permissions** (600 = user-only)
3. ✅ **Session expiration** (8 hours)
4. ✅ **OS keyring encryption** (OS-level)
5. ⚠️ **Keyring unlock state** (depends on user login)

### Recommended Improvements

#### 1. Process Validation (High Priority)
```python
# Only allow trusted processes to use cache
TRUSTED_PROCESSES = ['glassdome', 'python', 'uvicorn']
if process_name not in TRUSTED_PROCESSES:
    require_password = True
```

#### 2. Encrypt Session Cache (Medium Priority)
```python
# Encrypt cache file with user-specific key
# Derived from user ID + system info
cache_key = derive_key_from_user_context()
encrypted_cache = encrypt(cache_data, cache_key)
```

#### 3. Daemon Approach (High Priority)
```python
# Single daemon process holds session
# Other processes connect via secure IPC (Unix socket)
# Daemon validates process identity before sharing secrets
```

#### 4. Audit Logging (Medium Priority)
```python
# Log all session access attempts
logger.info(f"Session accessed by process: {os.getpid()}, user: {os.getuid()}")
```

#### 5. Keyring Lock Detection (Medium Priority)
```python
# Check if keyring is locked
# If locked, require password even if cache exists
if keyring_is_locked():
    require_password = True
```

## Best Practices

### For Users

1. **Lock keyring when not in use**
   - Linux: `secret-tool lock`
   - macOS: Keychain Access → Lock Keychain
   - Windows: Credential Manager locks automatically

2. **Use separate user accounts** for different security levels
   - Don't run untrusted code as the same user

3. **Monitor session cache file**
   ```bash
   ls -la ~/.glassdome/session_cache.json
   # Should show 600 permissions
   ```

4. **Log out when not using Glassdome**
   - Keyring typically locks on logout

### For Developers

1. **Don't store secrets in cache** ✅ (already done)
2. **Validate process identity** (recommended)
3. **Use daemon approach** for production (recommended)
4. **Add audit logging** (recommended)

## Comparison: Current vs. Alternatives

### Current Approach (OS Keyring + Cache)

**Pros:**
- ✅ Simple implementation
- ✅ Works across processes
- ✅ OS-level encryption for keyring
- ✅ No password prompts after first auth

**Cons:**
- ⚠️ Keyring accessible if unlocked
- ⚠️ Same-user processes can access
- ⚠️ Cache file indicates session exists

### Alternative 1: Daemon Process

**Pros:**
- ✅ Centralized session management
- ✅ Can validate process identity
- ✅ Better audit trail
- ✅ Can enforce additional security

**Cons:**
- ❌ More complex
- ❌ Requires daemon management
- ❌ IPC overhead

### Alternative 2: Encrypted Cache with User Key

**Pros:**
- ✅ Cache file encrypted
- ✅ User-specific encryption key
- ✅ Better than plain metadata

**Cons:**
- ⚠️ Still accessible if user compromised
- ⚠️ Key derivation must be secure

### Alternative 3: No Cross-Process Sharing

**Pros:**
- ✅ Maximum security
- ✅ Each process requires password

**Cons:**
- ❌ Poor user experience
- ❌ Password prompts for every process

## Conclusion

The current approach provides a **reasonable balance** between security and usability:

- **Low risk** if keyring is locked
- **Medium risk** if keyring is unlocked (user logged in)
- **High risk** if attacker has user-level access + keyring unlocked

**Recommendation:** 
- Use current approach for development
- Implement daemon approach for production
- Add process validation and audit logging
- Document keyring security best practices

## References

- [Linux Secret Service](https://specifications.freedesktop.org/secret-service/)
- [macOS Keychain Services](https://developer.apple.com/documentation/security/keychain_services)
- [Windows Credential Manager](https://docs.microsoft.com/en-us/windows/win32/api/wincred/)

