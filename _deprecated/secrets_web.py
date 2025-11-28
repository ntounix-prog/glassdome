"""
Web Interface for Secrets Management

Simple web form to set up and manage secrets.
"""
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.core.secrets import get_secrets_manager
from glassdome.core.paths import MASTER_KEY_PATH, SECRET_NAMES_PATH, PROJECT_ROOT as GLASSDOME_ROOT

app = FastAPI(title="Glassdome Secrets Manager", version="1.0.0")

# HTML template for the secrets management interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Glassdome Secrets Manager</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }
        input[type="password"], input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="password"]:focus, input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        .alert {
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .secrets-list {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 2px solid #e0e0e0;
        }
        .secret-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .secret-name {
            font-weight: 500;
            color: #333;
        }
        .secret-actions {
            display: flex;
            gap: 10px;
        }
        .btn-small {
            padding: 6px 12px;
            font-size: 12px;
            width: auto;
        }
        .btn-danger {
            background: #dc3545;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn-primary {
            background: #007bff;
        }
        .btn-primary:hover {
            background: #0056b3;
        }
        .btn-success {
            background: #28a745;
        }
        .btn-success:hover {
            background: #218838;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: white;
            margin: 15% auto;
            padding: 30px;
            border-radius: 12px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: #000;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Secrets Manager</h1>
        <p class="subtitle">Secure storage for passwords, tokens, and API keys</p>
        
        <div id="message"></div>
        
        <div id="secretsSection">
            <div class="secrets-list">
                <h2 style="margin-bottom: 20px; font-size: 20px;">Manage Secrets</h2>
                
                <div style="margin-bottom: 30px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="margin: 0; font-size: 18px;">Secrets</h3>
                        <button class="btn-small btn-primary" onclick="openAddNewKeyModal()" style="width: auto;">Add New Key</button>
                    </div>
                    <div id="secretsList" style="display: flex; flex-direction: column; gap: 12px;">
                        <!-- Secrets will be loaded here -->
                    </div>
                </div>
                
                <!-- Update Secret Modal -->
                <div id="updateModal" class="modal">
                    <div class="modal-content">
                        <span class="close" onclick="closeUpdateModal()">&times;</span>
                        <h2 style="margin-bottom: 20px;" id="updateModalTitle">Update Secret</h2>
                        <form id="updateSecretForm" method="POST" action="/update">
                            <input type="hidden" id="update_secret_key" name="secret_key">
                            <div class="form-group">
                                <label for="update_master_password">Master Password</label>
                                <input type="password" id="update_master_password" name="master_password" required 
                                       placeholder="Enter your master password">
                            </div>
                            <div class="form-group">
                                <label for="update_secret_value">New Secret Value</label>
                                <input type="password" id="update_secret_value" name="secret_value" required 
                                       placeholder="Enter new secret value">
                            </div>
                            <button type="submit">Update Secret</button>
                        </form>
                    </div>
                </div>
                
                <!-- Add New Key Modal -->
                <div id="addNewKeyModal" class="modal">
                    <div class="modal-content">
                        <span class="close" onclick="closeAddNewKeyModal()">&times;</span>
                        <h2 style="margin-bottom: 20px;">Add New Secret Key</h2>
                        <form id="addNewKeyForm" method="POST" action="/add-key">
                            <div class="form-group">
                                <label for="new_key_name">Secret Name (Human-readable)</label>
                                <input type="text" id="new_key_name" name="key_name" required 
                                       placeholder="e.g., Custom API Key, Database Password, etc.">
                            </div>
                            <div class="form-group">
                                <label for="add_master_password">Master Password</label>
                                <input type="password" id="add_master_password" name="master_password" required 
                                       placeholder="Enter your master password">
                            </div>
                            <div class="form-group">
                                <label for="add_secret_value">Secret Value</label>
                                <input type="password" id="add_secret_value" name="secret_value" required 
                                       placeholder="Enter the secret value">
                            </div>
                            <button type="submit">Add Secret</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Load and display secrets
        async function loadSecrets() {
            try {
                const response = await fetch('/list');
                const data = await response.json();
                const storedSecrets = new Set(data.secrets || []);
                const secretNames = data.secret_names || {}; // Mapping of key -> human-readable name
                
                const listDiv = document.getElementById('secretsList');
                listDiv.innerHTML = '';
                
                // Standard secrets with predefined names
                const standardSecrets = [
                    { key: 'proxmox_password', name: 'Proxmox Password' },
                    { key: 'proxmox_admin_passwd', name: 'Proxmox Admin Password (Legacy)' },
                    { key: 'proxmox_token_value', name: 'Proxmox Token (Instance 01)' },
                    { key: 'proxmox_token_value_02', name: 'Proxmox Token (Instance 02)' },
                    { key: 'proxmox_token_value_03', name: 'Proxmox Token (Instance 03)' },
                    { key: 'esxi_password', name: 'ESXi Password' },
                    { key: 'azure_client_secret', name: 'Azure Client Secret' },
                    { key: 'aws_secret_access_key', name: 'AWS Secret Access Key' },
                    { key: 'openai_api_key', name: 'OpenAI API Key' },
                    { key: 'anthropic_api_key', name: 'Anthropic API Key' },
                    { key: 'xai_api_key', name: 'X.AI API Key' },
                    { key: 'perplexity_api_key', name: 'Perplexity API Key' },
                    { key: 'rapidapi_key', name: 'RapidAPI Key' },
                    { key: 'google_search_api_key', name: 'Google Search API Key' },
                    { key: 'google_engine_id', name: 'Google Engine ID' },
                    { key: 'mail_api', name: 'Mailcow API Token' },
                    { key: 'secret_key', name: 'JWT Secret Key' }
                ];
                
                // Add all standard secrets
                standardSecrets.forEach(secret => {
                    const isSet = storedSecrets.has(secret.key);
                    const dotColor = isSet ? '#28a745' : '#007bff';
                    
                    const item = document.createElement('div');
                    item.style.cssText = 'display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 6px;';
                    item.innerHTML = `
                        <span style="width: 12px; height: 12px; border-radius: 50%; background: ${dotColor}; display: inline-block;"></span>
                        <span style="flex: 1; font-size: 14px;">${secret.name}</span>
                        <button class="btn-small btn-primary" onclick="openUpdateModal('${secret.key}', '${secret.name}')">Reset</button>
                    `;
                    listDiv.appendChild(item);
                });
                
                // Add custom secrets (those with names in secretNames but not in standardSecrets)
                const standardKeys = new Set(standardSecrets.map(s => s.key));
                Object.entries(secretNames).forEach(([key, name]) => {
                    if (!standardKeys.has(key)) {
                        const isSet = storedSecrets.has(key);
                        const dotColor = isSet ? '#28a745' : '#007bff';
                        
                        const item = document.createElement('div');
                        item.style.cssText = 'display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 6px;';
                        item.innerHTML = `
                            <span style="width: 12px; height: 12px; border-radius: 50%; background: ${dotColor}; display: inline-block;"></span>
                            <span style="flex: 1; font-size: 14px;">${name}</span>
                            <button class="btn-small btn-primary" onclick="openUpdateModal('${key}', '${name}')">Reset</button>
                        `;
                        listDiv.appendChild(item);
                    }
                });
            } catch (error) {
                console.error('Error loading secrets:', error);
            }
        }
        
        // Check if secrets manager is initialized and load secrets
        fetch('/status')
            .then(r => r.json())
            .then(data => {
                if (data.initialized) {
                    loadSecrets();
                }
            })
            .catch(e => console.log('Error checking status'));
        
        function openAddNewKeyModal() {
            document.getElementById('addNewKeyModal').style.display = 'block';
        }
        
        function closeAddNewKeyModal() {
            document.getElementById('addNewKeyModal').style.display = 'none';
            document.getElementById('addNewKeyForm').reset();
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const updateModal = document.getElementById('updateModal');
            const addModal = document.getElementById('addNewKeyModal');
            if (event.target == updateModal) {
                closeUpdateModal();
            }
            if (event.target == addModal) {
                closeAddNewKeyModal();
            }
        }
        
        // Add new key form submission
        document.getElementById('addNewKeyForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/add-key', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.success) {
                    showMessage('✅ Secret added successfully!', 'success');
                    closeAddNewKeyModal();
                    loadSecrets();
                } else {
                    showMessage('❌ ' + data.error, 'error');
                }
            } catch (error) {
                showMessage('❌ Error: ' + error.message, 'error');
            }
        });
        
        
        function openUpdateModal(key, name) {
            document.getElementById('update_secret_key').value = key;
            const modalTitle = document.getElementById('updateModalTitle');
            if (modalTitle) {
                modalTitle.textContent = `Reset ${name}`;
            }
            document.getElementById('updateModal').style.display = 'block';
            document.getElementById('updateSecretForm').reset();
            document.getElementById('update_secret_key').value = key;
        }
        
        function closeUpdateModal() {
            document.getElementById('updateModal').style.display = 'none';
            document.getElementById('updateSecretForm').reset();
        }
        
        
        // Update secret form submission
        document.getElementById('updateSecretForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/update', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.success) {
                    showMessage('✅ Secret updated successfully!', 'success');
                    closeUpdateModal();
                    loadSecrets();
                } else {
                    showMessage('❌ ' + data.error, 'error');
                }
            } catch (error) {
                showMessage('❌ Error: ' + error.message, 'error');
            }
        });
        
        async function deleteSecret(key) {
            if (!confirm(`Delete secret "${key}"?`)) return;
            
            try {
                const response = await fetch(`/delete/${key}`, { method: 'DELETE' });
                const data = await response.json();
                
                if (data.success) {
                    showMessage('✅ Secret deleted', 'success');
                    loadSecrets();
                } else {
                    showMessage('❌ ' + data.error, 'error');
                }
            } catch (error) {
                showMessage('❌ Error: ' + error.message, 'error');
            }
        }
        
        
        function showMessage(message, type) {
            const msgDiv = document.getElementById('message');
            msgDiv.className = `alert alert-${type}`;
            msgDiv.textContent = message;
            msgDiv.style.display = 'block';
            
            setTimeout(() => {
                msgDiv.style.display = 'none';
            }, 5000);
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the secrets management interface"""
    return HTML_TEMPLATE


@app.get("/status")
async def status():
    """Check if secrets manager is initialized"""
    try:
        secrets = get_secrets_manager()
        # Try to access the master key (will prompt if not initialized)
        # For web interface, we'll check if the encrypted file exists
        initialized = MASTER_KEY_PATH.exists()
        
        return {
            "initialized": initialized,
            "keyring_available": secrets._use_keyring
        }
    except Exception as e:
        return {
            "initialized": False,
            "error": str(e)
        }


@app.post("/setup")
async def setup(master_password: str = Form(...), confirm_password: str = Form(...)):
    """Initialize the secrets manager with a master password"""
    if master_password != confirm_password:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Passwords do not match"}
        )
    
    try:
        secrets = get_secrets_manager()
        
        # Check if already initialized
        if MASTER_KEY_PATH.exists():
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Secrets manager already initialized"}
            )
        
        # Manually initialize the master key
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        import os
        
        # Generate master key
        master_key = Fernet.generate_key()
        
        # Store master key encrypted with user password
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        fernet = Fernet(key)
        encrypted_master = fernet.encrypt(master_key)
        
        # Save encrypted master key
        master_key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(master_key_path, 'wb') as f:
            f.write(salt + encrypted_master)
        
        # Store in keyring if available
        if secrets._use_keyring:
            try:
                import keyring
                keyring.set_password(
                    secrets.SERVICE_NAME,
                    secrets.MASTER_KEY_NAME,
                    base64.b64encode(master_key).decode()
                )
            except Exception:
                pass
        
        # Set the master key in the instance
        secrets._master_key = master_key
        
        return JSONResponse(content={"success": True, "message": "Secrets manager initialized"})
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


def _load_master_key(secrets, master_password):
    """Helper to load master key using password"""
    if not MASTER_KEY_PATH.exists():
        raise ValueError("Secrets manager not initialized")
    
    if secrets._master_key is not None:
        return  # Already loaded
    
    if not master_password:
        raise ValueError("Master password required to access secrets")
    
    # Decrypt master key using password
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    
    with open(MASTER_KEY_PATH, 'rb') as f:
        salt = f.read(16)
        encrypted_key = f.read()
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    fernet = Fernet(key)
    secrets._master_key = fernet.decrypt(encrypted_key)


@app.post("/set")
async def set_secret(
    secret_key: str = Form(...), 
    secret_value: str = Form(...),
    master_password: str = Form(None)
):
    """Store a secret (creates new or updates existing)"""
    try:
        secrets = get_secrets_manager()
        _load_master_key(secrets, master_password)
        
        if secrets.set_secret(secret_key, secret_value):
            return JSONResponse(content={"success": True, "message": f"Secret '{secret_key}' stored"})
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to store secret"}
            )
            
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/update")
async def update_secret(
    secret_key: str = Form(...),
    secret_value: str = Form(...),
    master_password: str = Form(...)
):
    """Update or create a secret (works for both new and existing secrets)"""
    try:
        secrets = get_secrets_manager()
        _load_master_key(secrets, master_password)
        
        # Check if secret exists (for informational message)
        existing = secrets.get_secret(secret_key)
        
        # Set the secret (creates if new, updates if exists)
        if secrets.set_secret(secret_key, secret_value):
            action = "updated" if existing else "created"
            return JSONResponse(content={
                "success": True, 
                "message": f"Secret '{secret_key}' {action} successfully"
            })
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to store secret"}
            )
            
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/list")
async def list_secrets():
    """List all stored secrets with their human-readable names"""
    try:
        secrets = get_secrets_manager()
        secret_keys = secrets.list_secrets()
        
        # Load secret name mappings
        import json
        secret_names = {}
        if SECRET_NAMES_PATH.exists():
            try:
                with open(SECRET_NAMES_PATH) as f:
                    secret_names = json.load(f)
            except Exception:
                pass
        
        return JSONResponse(content={
            "secrets": secret_keys,
            "secret_names": secret_names
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/add-key")
async def add_new_key(
    key_name: str = Form(...),
    secret_value: str = Form(...),
    master_password: str = Form(...)
):
    """Add a new secret with a human-readable name"""
    try:
        secrets = get_secrets_manager()
        _load_master_key(secrets, master_password)
        
        # Generate internal key name from human-readable name
        import re
        internal_key = re.sub(r'[^a-z0-9_]', '_', key_name.lower().strip())
        internal_key = re.sub(r'_+', '_', internal_key)  # Replace multiple underscores
        internal_key = internal_key.strip('_')  # Remove leading/trailing underscores
        
        # Ensure it's unique by appending number if needed
        existing_keys = secrets.list_secrets()
        base_key = internal_key
        counter = 1
        while internal_key in existing_keys:
            internal_key = f"{base_key}_{counter}"
            counter += 1
        
        # Store the secret
        if secrets.set_secret(internal_key, secret_value):
            # Store the name mapping
            import json
            secret_names = {}
            if SECRET_NAMES_PATH.exists():
                try:
                    with open(SECRET_NAMES_PATH) as f:
                        secret_names = json.load(f)
                except Exception:
                    pass
            
            secret_names[internal_key] = key_name
            SECRET_NAMES_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SECRET_NAMES_PATH, 'w') as f:
                json.dump(secret_names, f, indent=2)
            
            return JSONResponse(content={
                "success": True,
                "message": f"Secret '{key_name}' added successfully",
                "internal_key": internal_key
            })
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to store secret"}
            )
            
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.delete("/delete/{secret_key}")
async def delete_secret(secret_key: str):
    """Delete a secret"""
    try:
        secrets = get_secrets_manager()
        if secrets.delete_secret(secret_key):
            # Remove from name mappings
            import json
            if SECRET_NAMES_PATH.exists():
                try:
                    with open(SECRET_NAMES_PATH) as f:
                        secret_names = json.load(f)
                    if secret_key in secret_names:
                        del secret_names[secret_key]
                        with open(SECRET_NAMES_PATH, 'w') as f:
                            json.dump(secret_names, f, indent=2)
                except Exception:
                    pass
            
            return JSONResponse(content={"success": True, "message": f"Secret '{secret_key}' deleted"})
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Secret not found"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/migrate")
async def migrate_secrets(master_password: str = Form(...)):
    """Migrate secrets from .env file to secure store"""
    try:
        secrets = get_secrets_manager()
        
        # Load master key using provided password
        if not MASTER_KEY_PATH.exists():
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Secrets manager not initialized"}
            )
        
        # Decrypt master key
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        with open(MASTER_KEY_PATH, 'rb') as f:
            salt = f.read(16)
            encrypted_key = f.read()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        fernet = Fernet(key)
        secrets._master_key = fernet.decrypt(encrypted_key)
        
        # Run migration (includes .env, .bashrc, and environment variables)
        env_file = PROJECT_ROOT / ".env"
        results = secrets.migrate_from_env(env_file, include_bashrc=True, include_environment=True)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        return JSONResponse(content={
            "success": True,
            "migrated": success_count,
            "total": total_count,
            "results": results
        })
        
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 70)
    print("  🔐 Glassdome Secrets Manager Web Interface")
    print("=" * 70)
    print("\n  Starting server on http://localhost:8002")
    print("  Open your browser and navigate to: http://localhost:8002")
    print("\n" + "=" * 70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8002)

