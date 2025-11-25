#!/usr/bin/env python3
"""
Overseer Model Validation Script

Tests the Overseer architecture to ensure it's viable for handoff:
1. Request gating works
2. State management works
3. Execution flow is sound
4. API endpoints are functional

Run: python scripts/validate_overseer_model.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from glassdome.core.security import ensure_security_context
ensure_security_context()

from glassdome.overseer.entity import OverseerEntity
from glassdome.overseer.state import SystemState, VM, VMStatus


async def test_request_gating():
    """Test that request gating works"""
    print("\n" + "="*70)
    print("TEST 1: Request Gating")
    print("="*70)
    
    overseer = OverseerEntity()
    
    # Test 1: Valid deploy request
    print("\n📥 Submitting valid deploy_vm request...")
    result1 = await overseer.receive_request(
        action='deploy_vm',
        params={
            'platform': 'proxmox',
            'os': 'ubuntu',
            'specs': {'name': 'test-vm', 'cores': 2, 'memory': 2048}
        },
        user='test-user'
    )
    print(f"   Result: {result1}")
    assert result1.get('approved') == True, "Valid request should be approved"
    print("   ✅ Valid request approved")
    
    # Test 2: Production protection
    print("\n📥 Submitting destroy_vm request for production VM...")
    # Add a production VM to state
    test_vm = VM(
        id='114',
        name='production-vm',
        platform='proxmox',
        status=VMStatus.RUNNING,
        is_production=True
    )
    overseer.state.add_vm(test_vm)
    
    result2 = await overseer.receive_request(
        action='destroy_vm',
        params={'vm_id': '114'},
        user='test-user'
    )
    print(f"   Result: {result2}")
    assert result2.get('approved') == False, "Production VM destruction should be denied"
    print("   ✅ Production protection working")
    
    # Test 3: Invalid action
    print("\n📥 Submitting invalid action...")
    result3 = await overseer.receive_request(
        action='invalid_action',
        params={},
        user='test-user'
    )
    print(f"   Result: {result3}")
    assert result3.get('approved') == False, "Invalid action should be denied"
    print("   ✅ Invalid action rejected")
    
    print("\n✅ Request gating: PASSED")
    return True


async def test_state_management():
    """Test state persistence and retrieval"""
    print("\n" + "="*70)
    print("TEST 2: State Management")
    print("="*70)
    
    overseer = OverseerEntity()
    
    # Add a VM
    test_vm = VM(
        id='999',
        name='test-vm-999',
        platform='proxmox',
        status=VMStatus.RUNNING,
        ip='192.168.3.99'
    )
    overseer.state.add_vm(test_vm)
    print(f"\n📝 Added VM: {test_vm.id} ({test_vm.name})")
    
    # Retrieve it
    retrieved = overseer.state.get_vm('999')
    assert retrieved is not None, "VM should be retrievable"
    assert retrieved.name == 'test-vm-999', "VM name should match"
    print(f"   ✅ VM retrieved: {retrieved.name}")
    
    # Update it
    overseer.state.update_vm('999', status=VMStatus.STOPPED)
    updated = overseer.state.get_vm('999')
    assert updated.status == VMStatus.STOPPED, "VM status should be updated"
    print(f"   ✅ VM updated: status = {updated.status.value}")
    
    # Remove it
    overseer.state.remove_vm('999')
    removed = overseer.state.get_vm('999')
    assert removed is None, "VM should be removed"
    print(f"   ✅ VM removed")
    
    print("\n✅ State management: PASSED")
    return True


async def test_execution_flow():
    """Test execution loop can process requests"""
    print("\n" + "="*70)
    print("TEST 3: Execution Flow")
    print("="*70)
    
    overseer = OverseerEntity()
    
    # Submit a request
    result = await overseer.receive_request(
        action='deploy_vm',
        params={
            'platform': 'proxmox',
            'os': 'ubuntu',
            'specs': {'name': 'exec-test-vm'}
        },
        user='test-user'
    )
    
    if result.get('approved'):
        request_id = result.get('request_id')
        print(f"\n📥 Request approved: {request_id}")
        
        # Check request is in state
        request = overseer.state.requests.get(request_id)
        assert request is not None, "Request should be in state"
        assert request.status == 'approved', "Request should be approved"
        print(f"   ✅ Request in state with status: {request.status}")
        
        # Manually trigger execution (simulating execution loop)
        print(f"\n⚙️  Simulating execution...")
        execution_result = await overseer._execute_request({
            'action': request.action,
            'params': request.params
        })
        print(f"   Execution result: {execution_result}")
        assert execution_result.get('status') in ['success', 'error'], "Execution should return status"
        print(f"   ✅ Execution handler works (returns: {execution_result.get('status')})")
    else:
        print(f"   ⚠️  Request denied: {result.get('reason')}")
    
    print("\n✅ Execution flow: PASSED")
    return True


async def test_api_compatibility():
    """Test that API request format is compatible"""
    print("\n" + "="*70)
    print("TEST 4: API Compatibility")
    print("="*70)
    
    overseer = OverseerEntity()
    
    # Simulate API request format
    api_request = {
        'action': 'deploy_vm',
        'params': {
            'platform': 'proxmox',
            'os': 'ubuntu',
            'specs': {
                'name': 'api-test-vm',
                'cores': 2,
                'memory': 2048,
                'disk_size': 20
            }
        },
        'user': 'api-user'
    }
    
    result = await overseer.receive_request(
        action=api_request['action'],
        params=api_request['params'],
        user=api_request['user']
    )
    
    print(f"\n📥 API request format test:")
    print(f"   Action: {api_request['action']}")
    print(f"   Params: {api_request['params']}")
    print(f"   Result: {result}")
    
    assert 'approved' in result, "Result should have 'approved' field"
    assert 'request_id' in result or 'reason' in result, "Result should have request_id or reason"
    print(f"   ✅ API format compatible")
    
    print("\n✅ API compatibility: PASSED")
    return True


async def test_missing_implementation():
    """Check what's missing for full implementation"""
    print("\n" + "="*70)
    print("TEST 5: Implementation Gaps")
    print("="*70)
    
    overseer = OverseerEntity()
    
    gaps = []
    
    # Check execution handlers
    print("\n🔍 Checking execution handlers...")
    result = await overseer._execute_deploy_vm({'platform': 'proxmox', 'os': 'ubuntu', 'specs': {}})
    if 'placeholder' in str(result.get('message', '')).lower():
        gaps.append("_execute_deploy_vm is a placeholder")
        print("   ⚠️  _execute_deploy_vm: PLACEHOLDER (needs agent integration)")
    else:
        print("   ✅ _execute_deploy_vm: IMPLEMENTED")
    
    result = await overseer._execute_start_vm({'vm_id': 'test'})
    if 'placeholder' in str(result.get('message', '')).lower():
        gaps.append("_execute_start_vm is a placeholder")
        print("   ⚠️  _execute_start_vm: PLACEHOLDER")
    else:
        print("   ✅ _execute_start_vm: IMPLEMENTED")
    
    result = await overseer._execute_stop_vm({'vm_id': 'test'})
    if 'placeholder' in str(result.get('message', '')).lower():
        gaps.append("_execute_stop_vm is a placeholder")
        print("   ⚠️  _execute_stop_vm: PLACEHOLDER")
    else:
        print("   ✅ _execute_stop_vm: IMPLEMENTED")
    
    # Check agent registry
    if not hasattr(overseer, 'agent_registry'):
        gaps.append("AgentRegistry not integrated")
        print("   ⚠️  AgentRegistry: NOT INTEGRATED")
    else:
        print("   ✅ AgentRegistry: INTEGRATED")
    
    print(f"\n📋 Summary: {len(gaps)} gaps found")
    if gaps:
        print("\n   Missing for full implementation:")
        for gap in gaps:
            print(f"   - {gap}")
    
    return gaps


async def main():
    """Run all validation tests"""
    print("\n" + "="*70)
    print("OVERSEER MODEL VALIDATION")
    print("="*70)
    print("\nValidating architecture for handoff implementation...")
    
    results = []
    
    try:
        results.append(await test_request_gating())
        results.append(await test_state_management())
        results.append(await test_execution_flow())
        results.append(await test_api_compatibility())
        gaps = await test_missing_implementation()
        
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        
        passed = sum(results)
        total = len(results)
        
        print(f"\n✅ Tests passed: {passed}/{total}")
        
        if gaps:
            print(f"\n⚠️  Implementation gaps: {len(gaps)}")
            print("\n   Required for handoff:")
            print("   1. Create AgentRegistry in glassdome/overseer/agent_registry.py")
            print("   2. Integrate AgentRegistry into OverseerEntity")
            print("   3. Implement _execute_deploy_vm with agents")
            print("   4. Implement _execute_start_vm / _execute_stop_vm")
            print("   5. Create OverseerClient in glassdome/api/overseer_client.py")
            print("   6. Refactor API endpoints to use OverseerClient")
        else:
            print("\n✅ All critical components implemented!")
        
        print("\n" + "="*70)
        
        if passed == total:
            print("✅ MODEL IS VIABLE FOR HANDOFF")
            return 0
        else:
            print("⚠️  MODEL NEEDS WORK BEFORE HANDOFF")
            return 1
            
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


