"""
Example: Testing A2A Communication
Demonstrates how to test agent-to-agent communication patterns
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib import A2AClient, AgentTimeoutError, AgentNotAvailableError


async def test_single_agent_call():
    """Test calling a single agent"""
    print("\n=== Test 1: Single Agent Call ===")
    
    async with A2AClient("TestClient") as client:
        try:
            result = await client.call_agent(
                agent_url="http://localhost:8081",
                task="analyze_diagram",
                payload={"image_uri": "gs://test/diagram.png"},
                timeout=30
            )
            print(f"✓ Success: {result}")
        except AgentTimeoutError as e:
            print(f"✗ Timeout: {e}")
        except AgentNotAvailableError as e:
            print(f"✗ Agent not available: {e}")
        except Exception as e:
            print(f"✗ Error: {e}")


async def test_parallel_agent_calls():
    """Test calling multiple agents in parallel"""
    print("\n=== Test 2: Parallel Agent Calls ===")
    
    async with A2AClient("TestClient") as client:
        calls = [
            {
                "agent_url": "http://localhost:8081",
                "task": "analyze_diagram",
                "payload": {"image_uri": "gs://test/diagram1.png"}
            },
            {
                "agent_url": "http://localhost:8082",
                "task": "find_donor",
                "payload": {"description": "microservices architecture"}
            },
            {
                "agent_url": "http://localhost:8083",
                "task": "write_section",
                "payload": {
                    "section": "Problem",
                    "description": "test",
                    "donor_context": {}
                }
            }
        ]
        
        try:
            results = await client.parallel_call(calls, fail_fast=False)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"  Call {i+1}: ✗ {result}")
                else:
                    print(f"  Call {i+1}: ✓ Success")
        except Exception as e:
            print(f"✗ Parallel call failed: {e}")


async def test_health_checks():
    """Test health check endpoints"""
    print("\n=== Test 3: Health Checks ===")
    
    agents = {
        "Vision": "http://localhost:8081",
        "Retrieval": "http://localhost:8082",
        "Writer": "http://localhost:8083",
        "Reviewer": "http://localhost:8084"
    }
    
    async with A2AClient("TestClient") as client:
        for name, url in agents.items():
            health = await client.check_health(url)
            status = health.get("status", "unknown")
            if status == "healthy":
                uptime = health.get("uptime_seconds", 0)
                print(f"  {name}: ✓ Healthy (uptime: {uptime:.1f}s)")
            else:
                print(f"  {name}: ✗ {status}")


async def test_capabilities_discovery():
    """Test capabilities endpoint"""
    print("\n=== Test 4: Capabilities Discovery ===")
    
    agents = {
        "Vision": "http://localhost:8081",
        "Retrieval": "http://localhost:8082",
        "Writer": "http://localhost:8083",
        "Reviewer": "http://localhost:8084"
    }
    
    async with A2AClient("TestClient") as client:
        for name, url in agents.items():
            capabilities = await client.get_capabilities(url)
            if capabilities:
                tasks = capabilities.get("supported_tasks", [])
                description = capabilities.get("description", "N/A")
                print(f"\n  {name} Agent:")
                print(f"    Description: {description}")
                print(f"    Supported Tasks: {', '.join(tasks)}")
            else:
                print(f"\n  {name}: ✗ Could not retrieve capabilities")


async def test_error_handling():
    """Test error handling scenarios"""
    print("\n=== Test 5: Error Handling ===")
    
    async with A2AClient("TestClient", max_retries=2) as client:
        
        # Test 1: Timeout scenario
        print("\n  Scenario 1: Timeout (1 second timeout)")
        try:
            await client.call_agent(
                agent_url="http://localhost:8081",
                task="slow_task",
                payload={},
                timeout=1
            )
            print("    ✗ Should have timed out")
        except AgentTimeoutError:
            print("    ✓ Correctly caught timeout")
        
        # Test 2: Agent not available
        print("\n  Scenario 2: Agent not available")
        try:
            await client.call_agent(
                agent_url="http://localhost:9999",  # Non-existent
                task="test",
                payload={}
            )
            print("    ✗ Should have failed")
        except AgentNotAvailableError:
            print("    ✓ Correctly caught unavailable agent")
        
        # Test 3: Invalid task
        print("\n  Scenario 3: Invalid task response")
        try:
            result = await client.call_agent(
                agent_url="http://localhost:8081",
                task="invalid_task",
                payload={}
            )
            print(f"    Result: {result}")
        except Exception as e:
            print(f"    ✓ Caught error: {type(e).__name__}")


async def test_request_tracing():
    """Test request ID propagation"""
    print("\n=== Test 6: Request Tracing ===")
    
    async with A2AClient("TestClient") as client:
        request_id = "test-trace-12345"
        
        try:
            result = await client.call_agent(
                agent_url="http://localhost:8081",
                task="analyze_diagram",
                payload={"image_uri": "gs://test/diagram.png"},
                request_id=request_id
            )
            print(f"  ✓ Request completed with ID: {request_id}")
            print(f"    Check agent logs for correlation")
        except Exception as e:
            print(f"  ✗ Request failed: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("A2A Communication Tests")
    print("=" * 60)
    print("\nNote: These tests assume agents are running on localhost")
    print("Start agents before running these tests.")
    print("\nPress Ctrl+C to skip any test\n")
    
    tests = [
        ("Single Agent Call", test_single_agent_call),
        ("Parallel Agent Calls", test_parallel_agent_calls),
        ("Health Checks", test_health_checks),
        ("Capabilities Discovery", test_capabilities_discovery),
        ("Error Handling", test_error_handling),
        ("Request Tracing", test_request_tracing),
    ]
    
    for test_name, test_func in tests:
        try:
            await test_func()
            await asyncio.sleep(0.5)  # Brief pause between tests
        except KeyboardInterrupt:
            print(f"\n⊗ Skipped: {test_name}")
            continue
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests cancelled by user")
