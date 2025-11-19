# Git & GitHub Setup Guide

## Initial Git Setup

### 1. Initialize Git Repository

```bash
cd /home/nomad/glassdome
git init
```

### 2. Configure Git (if not already done)

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 3. Initial Commit

```bash
# Stage all files
git add .

# Create initial commit
git commit -m "Initial commit: Full-stack project setup with Python, React, and Docker"
```

## GitHub Setup

### 1. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `glassdome`
3. Description: "Full-stack web application with Python/FastAPI backend and React frontend"
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### 2. Connect to GitHub

```bash
# Add GitHub as remote
git remote add origin https://github.com/YOUR_USERNAME/glassdome.git

# Or with SSH (recommended)
git remote add origin git@github.com:YOUR_USERNAME/glassdome.git

# Verify remote
git remote -v
```

### 3. Push to GitHub

```bash
# Push main branch
git branch -M main
git push -u origin main
```

## Recommended: Add GitHub Repository Settings

### Branch Protection (Optional)

1. Go to Settings → Branches
2. Add rule for `main` branch:
   - Require pull request reviews
   - Require status checks to pass
   - Do not allow force push

### Topics/Tags

Add these topics to your repository for discoverability:
- `python`
- `react`
- `fastapi`
- `docker`
- `full-stack`
- `vite`
- `rest-api`

### Repository Description

```
Full-stack web application with Python/FastAPI backend, React frontend, and Docker deployment
```

### Website

```
https://your-domain.com (or leave blank)
```

## .gitignore Verification

Your `.gitignore` is already configured to exclude:
- ✅ Python cache and virtual environments
- ✅ Node modules
- ✅ Environment files (.env)
- ✅ IDE files
- ✅ Build artifacts
- ✅ Log files

## Commit Message Conventions

Use conventional commits for better changelog generation:

```bash
# Features
git commit -m "feat: Add user authentication"

# Bug fixes
git commit -m "fix: Resolve CORS issue in API"

# Documentation
git commit -m "docs: Update setup instructions"

# Styling
git commit -m "style: Format code with Black"

# Refactoring
git commit -m "refactor: Reorganize backend modules"

# Tests
git commit -m "test: Add API endpoint tests"

# Chores
git commit -m "chore: Update dependencies"
```

## Recommended GitHub Workflows

### 1. Feature Branch Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: Add your feature"

# Push to GitHub
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

### 2. Keep Main Branch Clean

```bash
# Update main branch
git checkout main
git pull origin main

# Create new feature branch
git checkout -b feature/new-feature
```

## Adding Collaborators

1. Go to Settings → Collaborators
2. Click "Add people"
3. Enter GitHub username or email
4. Choose permission level

## Setting Up GitHub Actions (Optional)

Create `.github/workflows/main.yml`:

```yaml
name: CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest
    
    - name: Build Docker image
      run: |
        docker-compose build
```

## Clone Repository (For Team Members)

```bash
# Clone with HTTPS
git clone https://github.com/YOUR_USERNAME/glassdome.git

# Or with SSH
git clone git@github.com:YOUR_USERNAME/glassdome.git

# Navigate to project
cd glassdome

# Run setup
./setup.sh
```

## Common Git Commands

```bash
# Check status
git status

# View changes
git diff

# Stage changes
git add <file>
git add .

# Commit changes
git commit -m "message"

# Push to remote
git push

# Pull from remote
git pull

# Create branch
git checkout -b branch-name

# Switch branch
git checkout branch-name

# View branches
git branch -a

# Delete branch
git branch -d branch-name

# View commit history
git log --oneline
```

## Troubleshooting

### Large Files

If you accidentally committed large files:

```bash
# Install git-lfs
git lfs install

# Track large files
git lfs track "*.zip"
git lfs track "*.psd"

# Add .gitattributes
git add .gitattributes
git commit -m "chore: Setup Git LFS"
```

### Remove Committed Secret

```bash
# Remove file from history
git rm --cached .env
git commit -m "chore: Remove .env from tracking"

# Change the secret immediately!
```

### Reset to Remote

```bash
# CAREFUL: This will discard local changes
git fetch origin
git reset --hard origin/main
```

## GitHub Features to Enable

- [ ] Issues - Track bugs and features
- [ ] Projects - Kanban boards
- [ ] Wiki - Additional documentation
- [ ] Discussions - Community forum
- [ ] Releases - Version management

## README Badge Ideas

Add to your README.md:

```markdown
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![React](https://img.shields.io/badge/react-18-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
```

## Security Best Practices

- ✅ Never commit `.env` files
- ✅ Use GitHub Secrets for sensitive data
- ✅ Enable 2FA on your GitHub account
- ✅ Review dependencies regularly
- ✅ Use branch protection rules
- ✅ Keep dependencies updated

---

**You're all set! Push your code and start collaborating!** 🚀

