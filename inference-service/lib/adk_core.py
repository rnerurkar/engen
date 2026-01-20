from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uvicorn
import logging
import time
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    """Status of agent task execution"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class AgentRequest(BaseModel):
    """Standard request format for agent-to-agent communication"""
    task: str = Field(..., description="The task or action to perform")
    payload: Dict[str, Any] = Field(..., description="Task-specific data")
    request_id: Optional[str] = Field(None, description="Unique request identifier for tracing")
    sender: Optional[str] = Field(None, description="Agent name that sent this request")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of request creation")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for task execution")
    timeout_seconds: Optional[int] = Field(30, description="Maximum execution time")

class AgentResponse(BaseModel):
    """Standard response format for agent-to-agent communication"""
    status: TaskStatus = Field(..., description="Status of the task execution")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    agent_name: str = Field(..., description="Name of agent that processed the request")
    request_id: Optional[str] = Field(None, description="Original request ID for correlation")
    execution_time_ms: Optional[float] = Field(None, description="Time taken to process")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class Message(BaseModel):
    """Message format for agent communication and logging"""
    content: str
    sender: str = ""
    timestamp: str = ""
    message_type: str = "info"  # info, warning, error, debug
    metadata: Optional[Dict[str, Any]] = None

class AgentMetrics(BaseModel):
    """Agent performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    uptime_seconds: float = 0.0

class ADKAgent:
    """
    Agent Development Kit (ADK) Base Agent
    Provides standard FastAPI-based agent with A2A communication patterns
    """
    
    def __init__(self, name: str, port: int = 8080, version: str = "1.0.0"):
        self.name = name
        self.port = port
        self.version = version
        self.app = FastAPI(
            title=f"{name} Agent",
            version=version,
            description=f"ADK Agent: {name}"
        )
        self.logger = logging.getLogger(name)
        self.start_time = time.time()
        
        # Metrics
        self.metrics = AgentMetrics()
        
        # Register routes
        self._register_routes()
        
        # Lifecycle hooks
        self.app.add_event_handler("startup", self.on_startup)
        self.app.add_event_handler("shutdown", self.on_shutdown)

    def _register_routes(self):
        """Register standard agent API endpoints"""
        
        @self.app.post("/invoke", response_model=AgentResponse)
        async def invoke_endpoint(req: AgentRequest):
            """Main task invocation endpoint"""
            return await self.handle(req)
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint with dependency verification"""
            health_status = {
                "status": "healthy",
                "agent": self.name,
                "version": self.version,
                "uptime_seconds": time.time() - self.start_time,
                "dependencies": {}
            }
            
            # Check dependencies
            try:
                dep_status = await self.check_dependencies()
                health_status["dependencies"] = dep_status
                
                # Mark unhealthy if any critical dependency is down
                for dep_name, dep_info in dep_status.items():
                    if not dep_info.get("healthy", True) and dep_info.get("critical", False):
                        health_status["status"] = "unhealthy"
                        break
            except Exception as e:
                self.logger.warning(f"Dependency check failed: {e}")
                health_status["dependencies"] = {"error": str(e)}
            
            return health_status
        
        @self.app.get("/health/live")
        async def liveness_check():
            """Kubernetes liveness probe - just checks if server is running"""
            return {"status": "alive"}
        
        @self.app.get("/health/ready")
        async def readiness_check():
            """Kubernetes readiness probe - checks if agent can serve traffic"""
            try:
                dep_status = await self.check_dependencies()
                for dep_name, dep_info in dep_status.items():
                    if not dep_info.get("healthy", True) and dep_info.get("critical", False):
                        return {"status": "not_ready", "reason": f"{dep_name} unavailable"}
                return {"status": "ready"}
            except Exception as e:
                return {"status": "not_ready", "reason": str(e)}
        
        @self.app.get("/metrics", response_model=AgentMetrics)
        async def get_metrics():
            """Get agent performance metrics"""
            self.metrics.uptime_seconds = time.time() - self.start_time
            return self.metrics
        
        @self.app.get("/capabilities")
        async def get_capabilities():
            """Describe agent capabilities"""
            return {
                "agent": self.name,
                "version": self.version,
                "supported_tasks": self.get_supported_tasks(),
                "description": self.get_description()
            }

    async def handle(self, req: AgentRequest) -> AgentResponse:
        """
        Handle incoming agent request with error handling and metrics
        """
        start_time = time.time()
        request_id = req.request_id or f"{self.name}-{int(time.time()*1000)}"
        
        self.logger.info(
            f"[{request_id}] Processing task: {req.task} from {req.sender or 'unknown'}"
        )
        self.metrics.total_requests += 1
        
        try:
            # Execute the task with timeout awareness
            result = await self.process(req)
            
            execution_time = (time.time() - start_time) * 1000
            self.metrics.successful_requests += 1
            self._update_average_response_time(execution_time)
            
            self.logger.info(
                f"[{request_id}] Task completed successfully in {execution_time:.2f}ms"
            )
            
            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result=result,
                agent_name=self.name,
                request_id=request_id,
                execution_time_ms=execution_time,
                metadata={
                    "task": req.task,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.metrics.failed_requests += 1
            
            self.logger.error(
                f"[{request_id}] Task failed: {str(e)}",
                exc_info=True
            )
            
            return AgentResponse(
                status=TaskStatus.FAILED,
                error=str(e),
                agent_name=self.name,
                request_id=request_id,
                execution_time_ms=execution_time,
                metadata={
                    "task": req.task,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def process(self, req: AgentRequest) -> Dict[str, Any]:
        """
        Main processing method to be implemented by subclasses
        Must return a dictionary with the result
        """
        raise NotImplementedError(f"Agent {self.name} must implement process() method")

    def _update_average_response_time(self, new_time_ms: float):
        """Update rolling average response time"""
        current_avg = self.metrics.average_response_time_ms
        total = self.metrics.successful_requests
        self.metrics.average_response_time_ms = (
            (current_avg * (total - 1) + new_time_ms) / total
        )

    async def on_startup(self):
        """Lifecycle hook called when agent starts"""
        self.logger.info(f"Agent {self.name} v{self.version} starting up...")
        await self.initialize()

    async def on_shutdown(self):
        """Lifecycle hook called when agent shuts down"""
        self.logger.info(f"Agent {self.name} shutting down...")
        await self.cleanup()

    async def initialize(self):
        """Override this method for custom initialization logic"""
        pass

    async def cleanup(self):
        """Override this method for custom cleanup logic"""
        pass

    async def check_dependencies(self) -> Dict[str, Any]:
        """
        Override to check health of dependencies (databases, APIs, etc.)
        Returns dict with dependency name -> {healthy: bool, critical: bool, details: str}
        """
        return {}

    def get_supported_tasks(self) -> List[str]:
        """Override to list supported task types"""
        return ["default"]

    def get_description(self) -> str:
        """Override to provide agent description"""
        return f"{self.name} Agent"

    async def start(self):
        """Async start method for agent initialization"""
        self.logger.info(f"Initializing {self.name} agent...")
        await self.initialize()
        self.logger.info(f"{self.name} agent initialized successfully")

    def run(self, host: str = "0.0.0.0", port: Optional[int] = None):
        """Run the agent server (blocking)"""
        port = port or self.port
        self.logger.info(f"Starting {self.name} on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

    async def run_async(self, host: str = "0.0.0.0", port: Optional[int] = None):
        """Run the agent server asynchronously"""
        port = port or self.port
        self.logger.info(f"Starting {self.name} on {host}:{port}")
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

# Alias for backward compatibility
Agent = ADKAgent

def setup_logging(level: str = "INFO"):
    """Setup comprehensive logging configuration"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)