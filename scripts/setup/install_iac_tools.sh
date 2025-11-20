#!/bin/bash
#
# Install Infrastructure as Code Tools for Glassdome
# This script installs Ansible and Terraform for deployment automation
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║   Glassdome IaC Tools Installer                                ║"
echo "║   Installing Ansible + Terraform                               ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        VER=$(lsb_release -sr)
    else
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    fi
    
    echo -e "${BLUE}Detected OS: ${OS} ${VER}${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Ansible
install_ansible() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  Installing Ansible"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    if command_exists ansible; then
        ANSIBLE_VERSION=$(ansible --version | head -n1 | cut -d' ' -f2 | tr -d '[]')
        echo -e "${GREEN}✓ Ansible already installed: v${ANSIBLE_VERSION}${NC}"
        
        read -p "Reinstall/upgrade? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    echo "Installing Ansible..."
    
    case "$OS" in
        ubuntu|debian)
            echo "Using apt package manager..."
            sudo apt-get update
            sudo apt-get install -y software-properties-common
            sudo add-apt-repository --yes --update ppa:ansible/ansible
            sudo apt-get install -y ansible
            ;;
        
        fedora|rhel|centos)
            echo "Using dnf/yum package manager..."
            sudo dnf install -y ansible || sudo yum install -y ansible
            ;;
        
        arch|manjaro)
            echo "Using pacman package manager..."
            sudo pacman -S --noconfirm ansible
            ;;
        
        darwin)
            echo "Using Homebrew..."
            if ! command_exists brew; then
                echo -e "${RED}✗ Homebrew not found. Install from https://brew.sh${NC}"
                exit 1
            fi
            brew install ansible
            ;;
        
        *)
            echo -e "${YELLOW}⚠ Unsupported OS. Trying pip install...${NC}"
            pip3 install --user ansible
            ;;
    esac
    
    # Verify installation
    if command_exists ansible; then
        ANSIBLE_VERSION=$(ansible --version | head -n1 | cut -d' ' -f2 | tr -d '[]')
        echo -e "${GREEN}✓ Ansible installed successfully: v${ANSIBLE_VERSION}${NC}"
    else
        echo -e "${RED}✗ Ansible installation failed${NC}"
        exit 1
    fi
}

# Install Terraform
install_terraform() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  Installing Terraform"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    if command_exists terraform; then
        TF_VERSION=$(terraform version | head -n1 | cut -d'v' -f2)
        echo -e "${GREEN}✓ Terraform already installed: v${TF_VERSION}${NC}"
        
        read -p "Reinstall/upgrade? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    echo "Installing Terraform..."
    
    # Get latest version
    TERRAFORM_VERSION=${TERRAFORM_VERSION:-"1.6.6"}
    echo "Target version: ${TERRAFORM_VERSION}"
    
    # Detect architecture
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)
            ARCH="amd64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            ;;
        armv7l)
            ARCH="arm"
            ;;
    esac
    
    # Detect platform
    PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
    
    echo "Platform: ${PLATFORM}_${ARCH}"
    
    case "$OS" in
        ubuntu|debian|fedora|rhel|centos|arch|manjaro)
            # Download Terraform
            TF_URL="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_${PLATFORM}_${ARCH}.zip"
            
            echo "Downloading from: ${TF_URL}"
            
            TMP_DIR=$(mktemp -d)
            cd "$TMP_DIR"
            
            if ! curl -fsSL "$TF_URL" -o terraform.zip; then
                echo -e "${RED}✗ Failed to download Terraform${NC}"
                exit 1
            fi
            
            # Extract
            unzip -q terraform.zip
            
            # Install
            sudo mv terraform /usr/local/bin/
            sudo chmod +x /usr/local/bin/terraform
            
            # Cleanup
            cd "$PROJECT_ROOT"
            rm -rf "$TMP_DIR"
            ;;
        
        darwin)
            echo "Using Homebrew..."
            if ! command_exists brew; then
                echo -e "${RED}✗ Homebrew not found. Install from https://brew.sh${NC}"
                exit 1
            fi
            brew tap hashicorp/tap
            brew install hashicorp/tap/terraform
            ;;
        
        *)
            echo -e "${RED}✗ Unsupported OS for automatic Terraform installation${NC}"
            echo "Download manually from: https://www.terraform.io/downloads"
            exit 1
            ;;
    esac
    
    # Verify installation
    if command_exists terraform; then
        TF_VERSION=$(terraform version | head -n1 | cut -d'v' -f2)
        echo -e "${GREEN}✓ Terraform installed successfully: v${TF_VERSION}${NC}"
    else
        echo -e "${RED}✗ Terraform installation failed${NC}"
        exit 1
    fi
}

# Install Python packages
install_python_packages() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  Installing Python Integration Packages"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    # Check if in virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "${YELLOW}⚠ Not in virtual environment${NC}"
        echo "Activating virtual environment..."
        
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        else
            echo -e "${RED}✗ Virtual environment not found. Run: bash scripts/setup/setup.sh${NC}"
            exit 1
        fi
    fi
    
    echo "Installing ansible and python-terraform packages..."
    pip install ansible python-terraform
    
    echo -e "${GREEN}✓ Python packages installed${NC}"
}

# Create configuration directories
create_directories() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  Creating Configuration Directories"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    mkdir -p glassdome/vulnerabilities/playbooks/{web,network,system,forensics}
    mkdir -p glassdome/vulnerabilities/terraform/{aws,azure,gcp}
    mkdir -p configs/ansible
    mkdir -p configs/terraform
    
    echo -e "${GREEN}✓ Directories created:${NC}"
    echo "  • glassdome/vulnerabilities/playbooks/"
    echo "  • glassdome/vulnerabilities/terraform/"
    echo "  • configs/ansible/"
    echo "  • configs/terraform/"
}

# Verify installations
verify_installations() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  Verifying Installations"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    ERRORS=0
    
    # Check Ansible
    if command_exists ansible; then
        ANSIBLE_VERSION=$(ansible --version | head -n1 | cut -d' ' -f2 | tr -d '[]')
        echo -e "${GREEN}✓ Ansible: v${ANSIBLE_VERSION}${NC}"
        ansible --version | head -n5 | tail -n4
    else
        echo -e "${RED}✗ Ansible not found${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    echo ""
    
    # Check Terraform
    if command_exists terraform; then
        TF_VERSION=$(terraform version -json | grep -o '"terraform_version":"[^"]*"' | cut -d'"' -f4)
        echo -e "${GREEN}✓ Terraform: v${TF_VERSION}${NC}"
        terraform version
    else
        echo -e "${RED}✗ Terraform not found${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    echo ""
    
    # Check Python packages
    if python3 -c "import ansible" 2>/dev/null; then
        ANSIBLE_PY_VERSION=$(python3 -c "import ansible; print(ansible.__version__)")
        echo -e "${GREEN}✓ ansible Python package: v${ANSIBLE_PY_VERSION}${NC}"
    else
        echo -e "${YELLOW}⚠ ansible Python package not found${NC}"
    fi
    
    if python3 -c "import terraform" 2>/dev/null; then
        echo -e "${GREEN}✓ python-terraform package: installed${NC}"
    else
        echo -e "${YELLOW}⚠ python-terraform package not found${NC}"
    fi
    
    echo ""
    
    if [ $ERRORS -eq 0 ]; then
        echo -e "${GREEN}✓ All verifications passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ ${ERRORS} error(s) found${NC}"
        return 1
    fi
}

# Main installation flow
main() {
    detect_os
    
    echo ""
    echo "This script will install:"
    echo "  1. Ansible (configuration management)"
    echo "  2. Terraform (infrastructure as code)"
    echo "  3. Python integration packages"
    echo ""
    read -p "Continue? (Y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Installation cancelled"
        exit 0
    fi
    
    # Install components
    install_ansible
    install_terraform
    install_python_packages
    create_directories
    
    # Verify
    echo ""
    if verify_installations; then
        echo ""
        echo "╔════════════════════════════════════════════════════════════════╗"
        echo "║                                                                ║"
        echo "║   ✓ Installation Complete!                                    ║"
        echo "║                                                                ║"
        echo "╚════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Next steps:"
        echo "  1. Test Ansible: ansible --version"
        echo "  2. Test Terraform: terraform version"
        echo "  3. Run verification: python scripts/tools/verify_iac_tools.py"
        echo ""
        echo "Documentation:"
        echo "  • Ansible playbooks: glassdome/vulnerabilities/playbooks/"
        echo "  • Terraform modules: glassdome/vulnerabilities/terraform/"
        echo ""
    else
        echo ""
        echo -e "${RED}Installation completed with errors. Please review the output above.${NC}"
        exit 1
    fi
}

# Run main function
main

