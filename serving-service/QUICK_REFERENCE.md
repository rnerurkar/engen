# Quick Reference: ADK & A2A Usage

## Table of Contents
1. [Creating an Agent](#creating-an-agent)
2. [Calling Other Agents](#calling-other-agents)
3. [Using Prompt Templates](#using-prompt-templates)
4. [Error Handling](#error-handling)
5. [Testing](#testing)

---

## Creating an Agent

```python
from lib import ADKAgent, AgentRequest, setup_logging
from typing import List

class MyAgent(ADKAgent):
    def __init__(self):
        super().__init__(
            name="MyAgent",
            port=8080,
            version="1.0.0"
        )
        self.model = None
    
    async def initialize(self):
        """Called on startup"""
        self.logger.info("Initializing...")
        # Initialize models, connections, etc.
        self.model = GenerativeModel("gemini-1.5-pro")
    
    async def cleanup(self):
        """Called on shutdown"""
        self.logger.info("Cleaning up...")
        # Close connections, save state, etc.
    
    async def process(self, req: AgentRequest) -> dict:
        """Main processing logic"""
        # Extract payload
        data = req.payload.get('data')
        
        # Process
        result = await self.model.generate_content_async(data)
        
        # Return dict
        return {"output": result.text}
    
    def get_supported_tasks(self) -> List[str]:
        """Declare what tasks this agent handles"""
        return ["task1", "task2", "task3"]
    
    def get_description(self) -> str:
        """Describe what this agent does"""
        return "MyAgent does X, Y, and Z"

# Run the agent
if __name__ == "__main__":
    setup_logging("INFO")
    agent = MyAgent()
    agent.run(host="0.0.0.0", port=8080)
```

---

## Calling Other Agents

### Single Call

```python
from lib import A2AClient

async def call_vision_agent(image_uri: str):
    async with A2AClient("CallerAgent") as client:
        result = await client.call_agent(
            agent_url="http://vision:8080",
            task="analyze_diagram",
            payload={"image_uri": image_uri},
            timeout=30,
            request_id="req-123"  # Optional, for tracing
        )
        return result
```

### Parallel Calls

```python
from lib import A2AClient

async def call_multiple_agents():
    async with A2AClient("Orchestrator") as client:
        calls = [
            {
                "agent_url": "http://vision:8080",
                "task": "analyze",
                "payload": {"image_uri": "gs://..."}
            },
            {
                "agent_url": "http://retrieval:8082",
                "task": "search",
                "payload": {"query": "microservices"}
            }
        ]
        
        results = await client.parallel_call(calls, fail_fast=False)
        return results
```

### With Error Handling

```python
from lib import A2AClient, AgentTimeoutError, AgentNotAvailableError

async def safe_agent_call(agent_url: str, task: str, payload: dict):
    async with A2AClient("MyAgent") as client:
        try:
            result = await client.call_agent(
                agent_url=agent_url,
                task=task,
                payload=payload,
                timeout=30
            )
            return result
        except AgentTimeoutError:
            # Handle timeout
            return {"error": "timeout"}
        except AgentNotAvailableError:
            # Handle unavailable agent
            return {"error": "unavailable"}
        except Exception as e:
            # Handle other errors
            return {"error": str(e)}
```

### Health Check

```python
from lib import A2AClient

async def check_agent_health(agent_url: str):
    async with A2AClient("Monitor") as client:
        health = await client.check_health(agent_url)
        
        if health.get("status") == "healthy":
            print(f"Agent is healthy. Uptime: {health.get('uptime_seconds')}s")
            return True
        else:
            print(f"Agent is unhealthy: {health}")
            return False
```

---

## Using Prompt Templates

### Vision Agent

```python
from lib import PromptTemplates

# Basic analysis
prompt = PromptTemplates.vision_analyze_architecture_diagram()

# With focus areas
prompt = PromptTemplates.vision_analyze_architecture_diagram(
    context={"focus_areas": "security patterns and data flows"}
)
```

### Retrieval Agent

```python
from lib import PromptTemplates

# Generate search queries
prompt = PromptTemplates.retrieval_semantic_search_query(
    description="Microservices architecture with event sourcing",
    search_type="pattern"
)

# Rank patterns
prompt = PromptTemplates.retrieval_pattern_ranking(
    candidates=candidate_list,
    query_context={"domain": "e-commerce", "scale": "high"}
)
```

### Writer Agent

```python
from lib import PromptTemplates

# Generate section
prompt = PromptTemplates.writer_generate_section(
    section_name="Problem",
    description="System description from vision agent",
    reference_content="Reference style to match",
    critique="",  # Empty on first iteration
    context={"domain": "fintech"}
)

# With critique (for revision)
prompt = PromptTemplates.writer_generate_section(
    section_name="Solution",
    description="...",
    reference_content="...",
    critique="Add more detail about scalability approach",
    context=None
)
```

### Reviewer Agent

```python
from lib import PromptTemplates

# Evaluate draft
prompt = PromptTemplates.reviewer_evaluate_draft(
    draft_content="The draft text to review...",
    section_name="Problem",
    evaluation_criteria={"min_score": 90}
)
```

### Custom Prompt Building

```python
from lib import PromptBuilder

# Add context to any prompt
base_prompt = "Analyze this text..."
enhanced = PromptBuilder.add_context_section(
    base_prompt,
    {"domain": "healthcare", "audience": "technical"}
)

# Add few-shot examples
with_examples = PromptBuilder.add_examples(
    base_prompt,
    [
        {"input": "example 1 input", "output": "example 1 output"},
        {"input": "example 2 input", "output": "example 2 output"}
    ]
)
```

---

## Error Handling

### Exception Hierarchy

```
A2AError (base)
├── AgentTimeoutError      # Call exceeded timeout
└── AgentNotAvailableError # Agent unreachable
```

### Handling Specific Errors

```python
from lib import A2AClient, AgentTimeoutError, AgentNotAvailableError, A2AError

async def robust_agent_call():
    async with A2AClient("MyAgent", max_retries=3) as client:
        try:
            result = await client.call_agent(
                agent_url="http://target:8080",
                task="process",
                payload={"data": "..."},
                timeout=30
            )
            return {"status": "success", "result": result}
            
        except AgentTimeoutError as e:
            # Specific handling for timeouts
            logger.error(f"Agent call timed out: {e}")
            return {"status": "timeout", "error": str(e)}
            
        except AgentNotAvailableError as e:
            # Specific handling for unavailable agents
            logger.error(f"Agent not available: {e}")
            return {"status": "unavailable", "error": str(e)}
            
        except A2AError as e:
            # Handle other A2A errors
            logger.error(f"A2A error: {e}")
            return {"status": "error", "error": str(e)}
            
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}
```

### Retry Configuration

```python
# Custom retry settings
async with A2AClient(
    "MyAgent",
    max_retries=5,
    retry_delay=2.0,  # Base delay in seconds
    default_timeout=60
) as client:
    result = await client.call_agent(...)
```

---

## Testing

### Test Agent Health

```python
import asyncio
from lib import A2AClient

async def test_health():
    async with A2AClient("Tester") as client:
        health = await client.check_health("http://localhost:8080")
        print(health)

asyncio.run(test_health())
```

### Test Agent Call

```python
import asyncio
from lib import A2AClient

async def test_call():
    async with A2AClient("Tester") as client:
        result = await client.call_agent(
            agent_url="http://localhost:8080",
            task="test_task",
            payload={"test": "data"},
            timeout=10
        )
        print(result)

asyncio.run(test_call())
```

### Test Capabilities

```python
import asyncio
from lib import A2AClient

async def test_capabilities():
    async with A2AClient("Tester") as client:
        caps = await client.get_capabilities("http://localhost:8080")
        print("Agent:", caps.get("agent"))
        print("Supported Tasks:", caps.get("supported_tasks"))
        print("Description:", caps.get("description"))

asyncio.run(test_capabilities())
```

### Full Integration Test

```python
import asyncio
from lib import A2AClient

async def integration_test():
    """Test full workflow"""
    async with A2AClient("TestOrchestrator") as client:
        # Step 1: Vision
        vision_result = await client.call_agent(
            agent_url="http://vision:8081",
            task="analyze_diagram",
            payload={"image_uri": "gs://test/diagram.png"}
        )
        
        # Step 2: Retrieval
        retrieval_result = await client.call_agent(
            agent_url="http://retrieval:8082",
            task="find_donor",
            payload={"description": vision_result["description"]}
        )
        
        # Step 3: Writer
        writer_result = await client.call_agent(
            agent_url="http://writer:8083",
            task="write_section",
            payload={
                "section": "Problem",
                "description": vision_result["description"],
                "donor_context": retrieval_result
            }
        )
        
        # Step 4: Reviewer
        review_result = await client.call_agent(
            agent_url="http://reviewer:8084",
            task="review_draft",
            payload={"draft": writer_result["text"]}
        )
        
        print(f"Final score: {review_result['overall_score']}")
        return review_result

asyncio.run(integration_test())
```

---

## API Endpoints

All agents expose these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/invoke` | POST | Execute task |
| `/health` | GET | Health check |
| `/metrics` | GET | Performance metrics |
| `/capabilities` | GET | Agent capabilities |

### Example Request to /invoke

```bash
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "task": "analyze_diagram",
    "payload": {"image_uri": "gs://bucket/diagram.png"},
    "request_id": "req-123",
    "sender": "TestClient",
    "timeout_seconds": 30
  }'
```

### Example Response

```json
{
  "status": "completed",
  "result": {
    "description": "Microservices architecture...",
    "components": [...]
  },
  "agent_name": "VisionAgent",
  "request_id": "req-123",
  "execution_time_ms": 1234.56,
  "metadata": {
    "task": "analyze_diagram",
    "timestamp": "2025-12-10T12:00:00Z"
  }
}
```

---

## Environment Variables

```bash
# Agent URLs for Orchestrator
VISION_AGENT_URL=http://vision:8081
RETRIEVAL_AGENT_URL=http://retrieval:8082
WRITER_AGENT_URL=http://writer:8083
REVIEWER_AGENT_URL=http://reviewer:8084

# GCP Configuration
GCP_PROJECT_ID=your-project
GCP_LOCATION=us-central1

# Logging
LOG_LEVEL=INFO
```

---

## Common Patterns

### Orchestration Pattern

```python
async def orchestrate_workflow(request):
    async with A2AClient("Orchestrator") as client:
        # Parallel initial calls
        vision, retrieval = await asyncio.gather(
            client.call_agent(vision_url, "analyze", {...}),
            client.call_agent(retrieval_url, "search", {...})
        )
        
        # Sequential dependent call
        writer = await client.call_agent(
            writer_url,
            "write",
            {"vision": vision, "retrieval": retrieval}
        )
        
        return writer
```

### Retry Loop Pattern

```python
async def retry_with_feedback(client, max_iterations=3):
    critique = ""
    for i in range(max_iterations):
        draft = await client.call_agent(
            writer_url,
            "write",
            {"critique": critique}
        )
        
        review = await client.call_agent(
            reviewer_url,
            "review",
            {"draft": draft["text"]}
        )
        
        if review["score"] >= 90:
            return draft
        
        critique = review["feedback"]
    
    return draft  # Return best effort
```

---

## See Also

- **Full Examples**: `examples/` directory
- **Detailed Review**: `REVIEW_ADK_A2A.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **API Documentation**: Generated from code docstrings
