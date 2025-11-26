# WhiteKnight Tools & Abilities

## Installed Tools

### SSH/Remote Access
| Tool | Package | Purpose | Validation Use |
|------|---------|---------|----------------|
| `sshpass` | sshpass | Non-interactive SSH password auth | Weak SSH credentials |
| `ssh` | openssh-client | SSH client | Key-based access, tunneling |
| `hydra` | hydra | Brute-force login cracker | Multiple protocol credential testing |

### Web Application Testing
| Tool | Package | Purpose | Validation Use |
|------|---------|---------|----------------|
| `sqlmap` | sqlmap | SQL injection detection | SQLi vulnerabilities |
| `nikto` | nikto | Web server scanner | General web vulnerabilities |
| `curl` | curl | HTTP client | Custom web requests, API testing |
| `wget` | wget | HTTP downloader | File retrieval, connectivity |
| `wpscan` | wpscan | WordPress scanner | WordPress vulnerabilities |
| `dirb` | dirb | Directory brute-forcer | Hidden paths/files |
| `gobuster` | gobuster | Directory/DNS enumeration | Faster directory scanning |

### Network Analysis
| Tool | Package | Purpose | Validation Use |
|------|---------|---------|----------------|
| `nmap` | nmap | Port scanner | Service detection, open ports |
| `netcat` | netcat-openbsd | Network utility | Reverse shells, port testing |
| `smbclient` | smbclient | SMB client | Anonymous SMB access |
| `enum4linux` | enum4linux | SMB enumeration | Windows/Samba enumeration |
| `snmpwalk` | snmp | SNMP enumeration | SNMP misconfigurations |

### Exploitation Framework
| Tool | Package | Purpose | Validation Use |
|------|---------|---------|----------------|
| `msfconsole` | metasploit-framework | Exploitation framework | Full exploit validation |
| `msfvenom` | metasploit-framework | Payload generator | Custom payloads |

### Password/Hash Tools
| Tool | Package | Purpose | Validation Use |
|------|---------|---------|----------------|
| `john` | john | Password cracker | Weak password validation |
| `hashcat` | hashcat | GPU password cracker | Hash cracking |
| `hash-identifier` | hash-identifier | Hash type detection | Identify hash algorithms |

### Privilege Escalation
| Tool | Package | Purpose | Validation Use |
|------|---------|---------|----------------|
| `linpeas` | (download) | Linux privesc enumeration | Sudo/SUID misconfigs |
| `linux-exploit-suggester` | (download) | Kernel exploit finder | Kernel vulnerabilities |

---

## Validation Abilities Matrix

### CREDENTIAL Exploits
```
┌─────────────────────────────┬──────────────────────────────────┐
│ Exploit                     │ WhiteKnight Validation           │
├─────────────────────────────┼──────────────────────────────────┤
│ Weak SSH Password           │ sshpass + ssh login attempt      │
│ Weak FTP Password           │ curl ftp:// or hydra             │
│ Weak MySQL Password         │ mysql client connection          │
│ Weak PostgreSQL Password    │ psql connection                  │
│ Weak RDP Password           │ hydra rdp or xfreerdp            │
│ Weak SMB Password           │ smbclient with creds             │
│ Weak Telnet Password        │ hydra telnet                     │
│ Default Web App Creds       │ curl POST to login endpoint      │
└─────────────────────────────┴──────────────────────────────────┘
```

### WEB Exploits
```
┌─────────────────────────────┬──────────────────────────────────┐
│ Exploit                     │ WhiteKnight Validation           │
├─────────────────────────────┼──────────────────────────────────┤
│ SQL Injection               │ sqlmap --batch --url             │
│ Stored XSS                  │ curl + check reflection          │
│ Reflected XSS               │ curl + payload in response       │
│ LFI (Local File Inclusion)  │ curl /etc/passwd test            │
│ RFI (Remote File Inclusion) │ curl with remote URL             │
│ Command Injection           │ curl + whoami payload            │
│ DVWA Installation           │ curl check for DVWA page         │
│ Directory Traversal         │ curl ../../../etc/passwd         │
│ Insecure Direct Object Ref  │ curl with modified IDs           │
│ Unrestricted File Upload    │ curl upload + execute            │
└─────────────────────────────┴──────────────────────────────────┘
```

### NETWORK Exploits
```
┌─────────────────────────────┬──────────────────────────────────┐
│ Exploit                     │ WhiteKnight Validation           │
├─────────────────────────────┼──────────────────────────────────┤
│ SMB Anonymous Access        │ smbclient -L -N                  │
│ SMB Null Session            │ rpcclient -U "" -N               │
│ NFS World Readable          │ showmount -e + mount             │
│ SNMP Default Community      │ snmpwalk -c public               │
│ Open Redis                  │ redis-cli INFO                   │
│ Open MongoDB                │ mongo --eval "db.stats()"        │
│ Exposed Docker API          │ curl http://target:2375/version  │
│ Unauth Kubernetes API       │ curl https://target:6443/api     │
│ Open Elasticsearch          │ curl http://target:9200          │
└─────────────────────────────┴──────────────────────────────────┘
```

### PRIVESC Exploits
```
┌─────────────────────────────┬──────────────────────────────────┐
│ Exploit                     │ WhiteKnight Validation           │
├─────────────────────────────┼──────────────────────────────────┤
│ Sudo NOPASSWD               │ ssh + sudo -l (check NOPASSWD)   │
│ SUID Binary Abuse           │ ssh + find / -perm -4000         │
│ Writable /etc/passwd        │ ssh + ls -la /etc/passwd         │
│ Writable Cron               │ ssh + ls -la /etc/cron*          │
│ Kernel Exploit              │ ssh + uname -r + searchsploit    │
│ Docker Group                │ ssh + id (check docker group)    │
│ Path Hijacking              │ ssh + echo $PATH analysis        │
└─────────────────────────────┴──────────────────────────────────┘
```

### MISCONFIG Exploits
```
┌─────────────────────────────┬──────────────────────────────────┐
│ Exploit                     │ WhiteKnight Validation           │
├─────────────────────────────┼──────────────────────────────────┤
│ World-Readable SSH Keys     │ ssh + ls -la ~/.ssh              │
│ Disabled Firewall           │ nmap full port scan              │
│ SSL/TLS Vulnerabilities     │ nmap --script ssl-* or sslscan   │
│ HTTP Instead of HTTPS       │ curl http:// works               │
│ Missing Security Headers    │ curl -I check headers            │
│ Debug Mode Enabled          │ curl + check error verbosity     │
│ Directory Listing           │ curl / check for Index of        │
└─────────────────────────────┴──────────────────────────────────┘
```

---

## Metasploit Modules for Auto-Validation

### Auxiliary Scanners (Fast, non-intrusive)
```ruby
# Credential Testing
auxiliary/scanner/ssh/ssh_login
auxiliary/scanner/ftp/ftp_login
auxiliary/scanner/smb/smb_login
auxiliary/scanner/mysql/mysql_login
auxiliary/scanner/mssql/mssql_login
auxiliary/scanner/postgres/postgres_login

# Service Enumeration
auxiliary/scanner/smb/smb_enumshares
auxiliary/scanner/smb/smb_version
auxiliary/scanner/http/http_version
auxiliary/scanner/ssh/ssh_version
auxiliary/scanner/portscan/tcp

# Web Vulnerabilities
auxiliary/scanner/http/sql_injection_sqli
auxiliary/scanner/http/wordpress_scanner
auxiliary/scanner/http/dir_scanner
```

### Exploit Modules (Confirms exploitability)
```ruby
# Common Exploits
exploit/unix/ftp/vsftpd_234_backdoor
exploit/multi/http/apache_mod_cgi_bash_env_exec  # Shellshock
exploit/linux/http/apache_mod_cgi_bash_env        # Shellshock
exploit/multi/samba/usermap_script               # Samba RCE
exploit/unix/misc/distcc_exec                    # DistCC RCE
```

---

## Adding New Tools

To add a new tool to WhiteKnight:

1. **Add to Dockerfile:**
```dockerfile
RUN apt-get install -y new-tool-package
```

2. **Add validator in agent/main.py:**
```python
async def validate_new_exploit(self, target_ip: str, config: Dict) -> ValidationResult:
    cmd = f"new-tool --target {target_ip}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    success = "SUCCESS_INDICATOR" in result.stdout
    return ValidationResult(
        status=ValidationStatus.SUCCESS if success else ValidationStatus.FAILED,
        exploit_type="NEW_TYPE",
        target_ip=target_ip,
        evidence=result.stdout
    )
```

3. **Register validator:**
```python
self.validators["NEW_TYPE"] = self.validate_new_exploit
```

---

## Future Enhancements

- [ ] Add Metasploit RPC integration for faster scans
- [ ] Add Burp Suite headless for complex web testing
- [ ] Add Nuclei for template-based scanning
- [ ] Add custom Nmap NSE scripts
- [ ] Add Windows-specific tools (mimikatz, bloodhound)
- [ ] Add cloud-specific tools (aws-cli, az-cli, gcloud)

