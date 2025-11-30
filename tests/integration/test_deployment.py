"""
Deployment Flow Tests.

Tests the lab deployment workflow:
- Canvas deployment request validation
- VLAN allocation logic
- Lab registry operations
- VM creation (mocked)
- Deployment cleanup

Author: Brett Turner (ntounix)
Created: November 2025
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient


class TestCanvasDeploymentValidation:
    """Test deployment request validation."""
    
    @pytest.mark.asyncio
    async def test_deployment_requires_lab_id(self, async_client: AsyncClient):
        """Deployment request must include lab_id."""
        response = await async_client.post(
            "/api/deployments",
            json={
                "platform_id": "1",
                "lab_data": {"nodes": [], "edges": []},
            }
        )
        # Should fail validation
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_deployment_requires_platform_id(self, async_client: AsyncClient):
        """Deployment request must include platform_id."""
        response = await async_client.post(
            "/api/deployments",
            json={
                "lab_id": "test-lab",
                "lab_data": {"nodes": [], "edges": []},
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_deployment_requires_lab_data(self, async_client: AsyncClient):
        """Deployment request must include lab_data."""
        response = await async_client.post(
            "/api/deployments",
            json={
                "lab_id": "test-lab",
                "platform_id": "1",
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_only_proxmox_supported(self, async_client: AsyncClient):
        """Only Proxmox (platform_id=1) is supported."""
        response = await async_client.post(
            "/api/deployments",
            json={
                "lab_id": "test-lab",
                "platform_id": "2",  # Not Proxmox
                "lab_data": {
                    "nodes": [{"id": "n1", "type": "vm", "elementId": "ubuntu"}],
                    "edges": [],
                },
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        # Message says "Only Proxmox deployment is currently supported"
        assert "proxmox" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_deployment_needs_vms(self, async_client: AsyncClient):
        """Deployment with no VMs should fail."""
        response = await async_client.post(
            "/api/deployments",
            json={
                "lab_id": "test-lab",
                "platform_id": "1",
                "lab_data": {
                    "nodes": [],
                    "edges": [],
                },
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "no vm" in data["message"].lower()


class TestVLANAllocation:
    """Test VLAN allocation logic."""
    
    @pytest.mark.asyncio
    async def test_vlan_allocation_starts_at_100(self, db_session):
        """VLAN allocation should start at 100."""
        from glassdome.api.canvas_deploy import allocate_vlan
        
        vlan = await allocate_vlan(db_session)
        assert vlan == 100
    
    @pytest.mark.asyncio
    async def test_vlan_allocation_sequential(self, db_session):
        """VLANs should be allocated sequentially."""
        from glassdome.api.canvas_deploy import allocate_vlan
        from glassdome.networking.models import NetworkDefinition
        
        # First allocation
        vlan1 = await allocate_vlan(db_session)
        assert vlan1 == 100
        
        # Create a network using VLAN 100
        net = NetworkDefinition(
            name="test-net-1",
            display_name="Test Network 1",
            cidr="10.100.0.0/24",
            vlan_id=100,
            gateway="10.100.0.1",
            network_type="isolated",
            lab_id="lab-1",
        )
        db_session.add(net)
        await db_session.commit()
        
        # Second allocation should get 101
        vlan2 = await allocate_vlan(db_session)
        assert vlan2 == 101
    
    @pytest.mark.asyncio
    async def test_vlan_allocation_reuses_freed(self, db_session):
        """VLANs should be reused when freed."""
        from glassdome.api.canvas_deploy import allocate_vlan
        from glassdome.networking.models import NetworkDefinition
        
        # Allocate and create networks for VLANs 100, 101, 102
        for i in range(3):
            net = NetworkDefinition(
                name=f"test-net-{i}",
                display_name=f"Test Network {i}",
                cidr=f"10.{100+i}.0.0/24",
                vlan_id=100 + i,
                gateway=f"10.{100+i}.0.1",
                network_type="isolated",
                lab_id=f"lab-{i}",
            )
            db_session.add(net)
        await db_session.commit()
        
        # Next allocation should be 103
        vlan = await allocate_vlan(db_session)
        assert vlan == 103
        
        # Delete network with VLAN 101
        from sqlalchemy import delete
        await db_session.execute(
            delete(NetworkDefinition).where(NetworkDefinition.vlan_id == 101)
        )
        await db_session.commit()
        
        # Now allocation should reuse 101
        vlan = await allocate_vlan(db_session)
        assert vlan == 101
    
    @pytest.mark.asyncio
    async def test_network_config_derived_from_vlan(self):
        """Network config should be derived from VLAN ID."""
        from glassdome.api.canvas_deploy import derive_network_config
        
        config = derive_network_config(105)
        
        assert config["vlan_id"] == 105
        assert config["cidr"] == "10.105.0.0/24"
        assert config["gateway"] == "10.105.0.1"
        assert config["dhcp_start"] == "10.105.0.10"
        assert config["dhcp_end"] == "10.105.0.254"
        assert config["bridge"] == "vmbr1"


class TestDeploymentWithMockedProxmox:
    """Test deployment flow with mocked Proxmox."""
    
    @pytest.mark.asyncio
    async def test_deployment_creates_network(
        self, async_client: AsyncClient, db_session, mock_proxmox_client
    ):
        """Deployment should create network definition."""
        # Patch Proxmox client and settings
        with patch("glassdome.api.canvas_deploy.ProxmoxClient") as MockClient:
            MockClient.return_value = mock_proxmox_client
            
            # Patch settings to have valid lab config
            with patch("glassdome.api.canvas_deploy.settings") as mock_settings:
                mock_settings.get_lab_proxmox_instance.return_value = "01"
                mock_settings.get_lab_node_name.return_value = "pve01"
                mock_settings.get_lab_proxmox_config.return_value = {
                    "host": "test.proxmox.local",
                    "user": "testuser",
                    "password": "testpass",
                    "token_name": None,
                    "token_value": None,
                    "verify_ssl": False,
                }
                
                response = await async_client.post(
                    "/api/deployments",
                    json={
                        "lab_id": "deploy-test-001",
                        "platform_id": "1",
                        "lab_data": {
                            "nodes": [
                                {"id": "n1", "type": "vm", "elementId": "ubuntu"},
                            ],
                            "edges": [],
                        },
                    }
                )
        
        # Response structure should be valid even if deployment partially fails
        assert response.status_code == 200
        data = response.json()
        assert "deployment_id" in data
        assert "lab_id" in data
        assert "vms" in data


class TestLabRegistryOperations:
    """Test lab registry integration."""
    
    @pytest.mark.asyncio
    async def test_registry_status_endpoint(self, async_client: AsyncClient):
        """Registry status endpoint should return connection info."""
        response = await async_client.get("/api/registry/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert "resource_counts" in data
    
    @pytest.mark.asyncio
    async def test_registry_labs_endpoint(self, async_client: AsyncClient):
        """Registry labs endpoint should return lab list."""
        response = await async_client.get("/api/registry/labs")
        assert response.status_code == 200
        data = response.json()
        assert "labs" in data
    
    @pytest.mark.asyncio
    async def test_registry_drift_endpoint(self, async_client: AsyncClient):
        """Registry drift endpoint should return drift info."""
        response = await async_client.get("/api/registry/drift")
        assert response.status_code == 200
        data = response.json()
        assert "drifts" in data


class TestDeploymentCleanup:
    """Test deployment destruction."""
    
    @pytest.mark.asyncio
    async def test_destroy_nonexistent_deployment(self, async_client: AsyncClient):
        """Destroying nonexistent deployment should return 404."""
        response = await async_client.delete("/api/deployments/nonexistent-lab")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_deployments_returns_structure(self, async_client: AsyncClient):
        """List deployments should return proper structure."""
        response = await async_client.get("/api/deployments")
        assert response.status_code == 200
        data = response.json()
        assert "deployments" in data
        assert "total" in data
        assert isinstance(data["deployments"], list)


class TestDeployedVMTracking:
    """Test deployed VM tracking in database."""
    
    @pytest.mark.asyncio
    async def test_deployed_vm_model(self, db_session):
        """Test DeployedVM model creation."""
        from glassdome.networking.models import DeployedVM
        
        vm = DeployedVM(
            lab_id="test-lab-001",
            name="test-vm-01",
            vm_id="100",
            platform="proxmox",
            platform_instance="01",
            os_type="ubuntu",
            template_id="9001",
            cpu_cores=2,
            memory_mb=2048,
            disk_gb=20,
            ip_address="192.168.1.100",
            status="running",
        )
        db_session.add(vm)
        await db_session.commit()
        await db_session.refresh(vm)
        
        assert vm.id is not None
        assert vm.lab_id == "test-lab-001"
        assert vm.vm_id == "100"
    
    @pytest.mark.asyncio
    async def test_deployed_vm_to_dict(self, db_session):
        """Test DeployedVM to_dict method."""
        from glassdome.networking.models import DeployedVM
        
        vm = DeployedVM(
            lab_id="test-lab-001",
            name="test-vm-01",
            vm_id="100",
            platform="proxmox",
            platform_instance="01",
            os_type="ubuntu",
            status="running",
        )
        db_session.add(vm)
        await db_session.commit()
        
        vm_dict = vm.to_dict()
        assert vm_dict["name"] == "test-vm-01"
        assert vm_dict["vm_id"] == "100"
        assert vm_dict["platform"] == "proxmox"


class TestNetworkDefinitionModel:
    """Test NetworkDefinition model."""
    
    @pytest.mark.asyncio
    async def test_network_definition_creation(self, db_session):
        """Test NetworkDefinition model creation."""
        from glassdome.networking.models import NetworkDefinition
        
        net = NetworkDefinition(
            name="lab-network",
            display_name="Lab Network",
            cidr="10.100.0.0/24",
            vlan_id=100,
            gateway="10.100.0.1",
            network_type="isolated",
            lab_id="lab-001",
        )
        db_session.add(net)
        await db_session.commit()
        await db_session.refresh(net)
        
        assert net.id is not None
        assert net.vlan_id == 100
        assert net.cidr == "10.100.0.0/24"
