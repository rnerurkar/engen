"""
Centralized Prompt Templates for All Agents
Provides structured, detailed prompts for consistent LLM interactions
"""

from typing import Dict, Any, Optional
from datetime import datetime

class PromptTemplates:
    """Manages all prompt templates for the agent swarm"""
    
    # ============================================================================
    # VISION AGENT PROMPTS
    # ============================================================================
    
    @staticmethod
    def vision_analyze_architecture_diagram(context: Optional[Dict[str, Any]] = None) -> str:
        """
        Comprehensive prompt for architectural diagram analysis
        Returns structured information about components, data flows, and patterns
        """
        base_prompt = """You are an expert Software Architect analyzing architectural diagrams.

**YOUR TASK:**
Analyze the provided architecture diagram and extract detailed technical information.

**ANALYSIS FRAMEWORK:**

1. **System Overview**
   - System name and type (e.g., microservices, monolithic, event-driven)
   - Primary business domain and purpose
   - Architectural style and patterns used

2. **Components Analysis**
   For each component, identify:
   - Component name and type (service, database, API, queue, etc.)
   - Technology stack (languages, frameworks, databases)
   - Primary responsibilities and functions
   - Deployment characteristics (containerized, serverless, VM-based)

3. **Data Flow Mapping**
   - Identify all data flows between components
   - Note the direction and type of communication (REST, gRPC, event, message queue)
   - Highlight synchronous vs asynchronous patterns
   - Identify data transformation points

4. **Integration Patterns**
   - API Gateways and their configurations
   - Message brokers and event buses
   - Service mesh or networking patterns
   - Authentication and authorization flows

5. **Infrastructure & Deployment**
   - Cloud provider and services used
   - Storage solutions (databases, object storage, caching)
   - Networking components (load balancers, CDNs, firewalls)
   - Monitoring and observability tools

6. **Design Patterns Identified**
   - Architectural patterns (CQRS, Event Sourcing, Saga, etc.)
   - Design patterns (Circuit Breaker, Retry, Rate Limiting, etc.)
   - Security patterns (OAuth, JWT, mTLS, etc.)

7. **Scalability & Resilience**
   - Horizontal vs vertical scaling capabilities
   - Redundancy and failover mechanisms
   - Performance optimization techniques
   - Disaster recovery considerations

**OUTPUT FORMAT:**
Provide a structured JSON response with the following schema:
```json
{
  "system_overview": {
    "name": "string",
    "type": "string",
    "domain": "string",
    "architectural_style": "string"
  },
  "components": [
    {
      "id": "string",
      "name": "string",
      "type": "string",
      "technology": ["string"],
      "responsibilities": ["string"]
    }
  ],
  "data_flows": [
    {
      "from": "component_id",
      "to": "component_id",
      "protocol": "string",
      "data_type": "string",
      "synchronous": boolean
    }
  ],
  "patterns": {
    "architectural": ["string"],
    "design": ["string"],
    "security": ["string"]
  },
  "infrastructure": {
    "cloud_provider": "string",
    "storage": ["string"],
    "networking": ["string"]
  },
  "technical_summary": "string (2-3 paragraphs)"
}
```

**IMPORTANT:**
- Be precise and technical
- Include all visible components
- Note any ambiguities or assumptions
- Focus on what can be directly observed in the diagram
"""
        
        if context and context.get('focus_areas'):
            base_prompt += f"\n\n**SPECIFIC FOCUS AREAS:**\n{context['focus_areas']}"
        
        return base_prompt

    # ============================================================================
    # RETRIEVAL AGENT PROMPTS
    # ============================================================================
    
    @staticmethod
    def retrieval_semantic_search_query(description: str, search_type: str = "pattern") -> str:
        """
        Generate enhanced search query for semantic retrieval
        """
        return f"""Generate optimized search queries for finding similar architectural patterns.

**INPUT DESCRIPTION:**
{description}

**SEARCH TYPE:** {search_type}

**YOUR TASK:**
Create 3-5 semantic search queries that will find the most relevant donor patterns from the knowledge base.

**QUERY REQUIREMENTS:**
1. Include key architectural terms and patterns
2. Focus on technical components and their relationships
3. Include domain-specific terminology
4. Vary abstraction levels (specific → general)
5. Consider synonyms and alternative phrasings

**OUTPUT FORMAT:**
Return JSON array of search queries with relevance weights:
```json
[
  {{"query": "string", "weight": 1.0, "focus": "exact_match"}},
  {{"query": "string", "weight": 0.8, "focus": "architectural_pattern"}},
  {{"query": "string", "weight": 0.6, "focus": "component_similarity"}},
  {{"query": "string", "weight": 0.4, "focus": "domain_context"}}
]
```
"""

    @staticmethod
    def retrieval_pattern_ranking(candidates: list, query_context: Dict[str, Any]) -> str:
        """
        Prompt for ranking retrieved patterns by relevance
        """
        return f"""Rank the following architectural patterns by their relevance to the query context.

**QUERY CONTEXT:**
{query_context}

**CANDIDATE PATTERNS:**
{candidates}

**RANKING CRITERIA:**
1. **Architectural Similarity (40%)**: How closely do the patterns match?
2. **Component Overlap (25%)**: Shared technologies and components
3. **Data Flow Patterns (20%)**: Similar communication patterns
4. **Domain Relevance (15%)**: Business domain alignment

**OUTPUT FORMAT:**
Return ranked list with scores:
```json
[
  {{
    "pattern_id": "string",
    "relevance_score": 0.95,
    "reasoning": "string",
    "key_similarities": ["string"],
    "key_differences": ["string"]
  }}
]
```

Sort by relevance_score (descending). Include top 5 matches only.
"""

    # ============================================================================
    # WRITER AGENT PROMPTS
    # ============================================================================
    
    @staticmethod
    def writer_generate_section(
        section_name: str,
        description: str,
        reference_content: str,
        critique: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Comprehensive prompt for generating documentation sections
        """
        prompt = f"""You are a Senior Technical Writer specializing in software architecture documentation.

**TASK:** Write the '{section_name}' section for architecture documentation

**PROJECT DESCRIPTION:**
{description}

**REFERENCE STYLE & CONTENT:**
The following is a high-quality example from a similar project. Match this style, structure, and technical depth:
---
{reference_content}
---

**SECTION REQUIREMENTS:**

"""
        
        # Section-specific guidelines
        section_guidelines = {
            "Problem": """
**Problem Statement Guidelines:**
1. **Context Setting** (1-2 paragraphs)
   - Business background and current situation
   - Stakeholders and their needs
   - Existing systems and limitations

2. **Core Challenges** (bullet points or paragraphs)
   - Technical challenges (scalability, performance, integration)
   - Business challenges (time-to-market, cost, compliance)
   - Organizational challenges (team skills, resources)

3. **Constraints & Requirements** (structured list)
   - Technical constraints (technology stack, infrastructure)
   - Business constraints (budget, timeline, compliance)
   - Quality attributes (performance, security, availability)

4. **Success Criteria**
   - Measurable outcomes and KPIs
   - Acceptance criteria for the solution
""",
            "Solution": """
**Solution Overview Guidelines:**
1. **High-Level Approach** (2-3 paragraphs)
   - Overall architectural strategy
   - Key design decisions and rationale
   - Alignment with requirements

2. **Architecture Components** (detailed description)
   - Core services and their responsibilities
   - Data storage and management
   - Integration points and APIs
   - Infrastructure and deployment

3. **Technology Choices** (justified selections)
   - Programming languages and frameworks (with rationale)
   - Databases and storage solutions (with rationale)
   - Cloud services and infrastructure (with rationale)
   - Third-party services and libraries (with rationale)

4. **Design Patterns & Principles**
   - Architectural patterns applied (microservices, event-driven, etc.)
   - Design patterns used (Circuit Breaker, CQRS, etc.)
   - SOLID principles and best practices

5. **Data Flow & Integration**
   - Request/response flows
   - Event propagation and handling
   - Data synchronization strategies
   - API contracts and versioning

6. **Non-Functional Requirements**
   - Scalability approach (horizontal/vertical, auto-scaling)
   - Performance optimization (caching, CDN, database indexing)
   - Security measures (authentication, authorization, encryption)
   - Reliability & resilience (redundancy, failover, disaster recovery)
   - Monitoring & observability (logging, metrics, tracing)
""",
            "Implementation": """
**Implementation Details Guidelines:**
1. **Development Approach**
   - Implementation phases and milestones
   - Team structure and responsibilities
   - Development methodology (Agile, Scrum, etc.)

2. **Code Organization**
   - Repository structure
   - Module boundaries
   - Dependency management

3. **Key Implementation Patterns**
   - Code-level design patterns
   - Testing strategies (unit, integration, e2e)
   - CI/CD pipeline configuration

4. **Deployment Strategy**
   - Environment setup (dev, staging, prod)
   - Deployment automation
   - Rollback procedures
""",
            "Trade-offs": """
**Trade-offs & Considerations Guidelines:**
1. **Design Trade-offs**
   - Performance vs. Complexity
   - Cost vs. Scalability
   - Flexibility vs. Simplicity
   - Time-to-market vs. Technical Debt

2. **Alternative Approaches Considered**
   - Other architectural options evaluated
   - Why they were not chosen
   - Scenarios where alternatives might be better

3. **Known Limitations**
   - Current system constraints
   - Areas for future improvement
   - Technical debt acknowledgment

4. **Risk Assessment**
   - Technical risks and mitigation
   - Business risks and contingencies
   - Dependencies on external factors
"""
        }
        
        prompt += section_guidelines.get(section_name, "Write a comprehensive, technical section that follows the reference style.")
        
        if critique:
            prompt += f"""

**PREVIOUS FEEDBACK TO ADDRESS:**
{critique}

**IMPORTANT:** Specifically address all points raised in the feedback above.
"""
        
        prompt += """

**WRITING STYLE REQUIREMENTS:**
- Use clear, professional technical language
- Be specific with technical details (versions, configurations, numbers)
- Use active voice where possible
- Include concrete examples and code snippets where appropriate
- Structure with clear headings and subheadings
- Use bullet points for lists and key points
- Include diagrams references where applicable (e.g., "See Figure 1")

**FORMAT:**
- Use Markdown formatting
- Include appropriate heading levels (##, ###, ####)
- Use code blocks with language specification for code examples
- Use tables for comparisons or structured data

**LENGTH:**
Aim for 800-1500 words for major sections (Problem, Solution)
Aim for 400-800 words for supporting sections

**OUTPUT:**
Return ONLY the section content in Markdown format. Do not include meta-commentary or explanations about your writing process.
"""
        
        if context:
            prompt += f"\n\n**ADDITIONAL CONTEXT:**\n{context}"
        
        return prompt

    # ============================================================================
    # REVIEWER AGENT PROMPTS
    # ============================================================================
    
    @staticmethod
    def reviewer_evaluate_draft(
        draft_content: str,
        section_name: str,
        evaluation_criteria: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Comprehensive prompt for reviewing and scoring documentation
        """
        return f"""You are a Senior Technical Reviewer specializing in software architecture documentation quality.

**YOUR TASK:**
Evaluate the quality of the '{section_name}' section draft and provide a detailed assessment.

**DRAFT TO REVIEW:**
---
{draft_content}
---

**EVALUATION FRAMEWORK:**

1. **Technical Accuracy & Depth (25 points)**
   - Are technical details correct and specific?
   - Is appropriate depth provided for the audience?
   - Are technology choices properly justified?
   - Are architectural patterns correctly applied?

2. **Completeness & Coverage (20 points)**
   - Are all required topics covered?
   - Is the information comprehensive?
   - Are there obvious gaps or missing details?
   - Are edge cases and constraints addressed?

3. **Clarity & Readability (20 points)**
   - Is the language clear and professional?
   - Is technical jargon used appropriately?
   - Are concepts explained well for the target audience?
   - Is the structure logical and easy to follow?

4. **Structure & Organization (15 points)**
   - Are headings and sections well-organized?
   - Does the narrative flow logically?
   - Are transitions smooth between topics?
   - Is formatting consistent and appropriate?

5. **Practical Value (10 points)**
   - Does it provide actionable information?
   - Are examples concrete and relevant?
   - Would this help developers implement the solution?
   - Are trade-offs and considerations clearly explained?

6. **Alignment with Reference Style (10 points)**
   - Does it match the expected style and tone?
   - Is the level of detail appropriate?
   - Does it follow similar structural patterns?

**SCORING:**
- 90-100: Excellent - Ready for publication with minor tweaks
- 80-89: Good - Needs minor revisions
- 70-79: Acceptable - Needs moderate improvements
- 60-69: Needs Work - Significant revisions required
- Below 60: Inadequate - Major rewrite needed

**OUTPUT FORMAT:**
Return a JSON object with the following structure:
```json
{{
  "overall_score": 85,
  "category_scores": {{
    "technical_accuracy": 22,
    "completeness": 18,
    "clarity": 17,
    "structure": 14,
    "practical_value": 8,
    "style_alignment": 9
  }},
  "strengths": [
    "Specific strength point 1",
    "Specific strength point 2",
    "Specific strength point 3"
  ],
  "improvements_needed": [
    {{
      "issue": "Specific issue description",
      "severity": "high|medium|low",
      "suggestion": "Concrete suggestion for improvement",
      "location": "Section or paragraph reference"
    }}
  ],
  "critical_issues": [
    "Critical issue that must be fixed"
  ],
  "revision_priority": "high|medium|low",
  "estimated_revision_effort": "major|moderate|minor",
  "detailed_feedback": "A comprehensive 2-3 paragraph narrative explaining the assessment, highlighting key issues and providing context for the scores."
}}
```

**IMPORTANT:**
- Be constructive and specific in feedback
- Provide actionable suggestions for improvement
- Balance criticism with recognition of strengths
- Focus on the most impactful improvements first
"""

    # ============================================================================
    # ORCHESTRATOR PROMPTS (Decision Making)
    # ============================================================================
    
    @staticmethod
    def orchestrator_plan_workflow(request: Dict[str, Any]) -> str:
        """
        Prompt for orchestrator to plan the agent workflow
        """
        return f"""You are the Orchestrator Agent managing a multi-agent workflow for architecture documentation generation.

**REQUEST:**
{request}

**AVAILABLE AGENTS:**
1. **Vision Agent**: Analyzes architecture diagrams to extract components, flows, and patterns
2. **Retrieval Agent**: Finds similar donor patterns from the knowledge base
3. **Writer Agent**: Generates documentation sections based on analysis and patterns
4. **Reviewer Agent**: Evaluates documentation quality and provides feedback

**YOUR TASK:**
Plan the optimal workflow execution strategy for this request.

**CONSIDERATIONS:**
- Which agents need to be invoked?
- In what sequence?
- What data needs to flow between agents?
- How many revision iterations are appropriate?
- What are the quality gates?

**OUTPUT FORMAT:**
```json
{{
  "workflow_plan": [
    {{
      "step": 1,
      "agent": "vision",
      "action": "analyze_diagram",
      "input_from": "request",
      "output_to": ["retrieval", "writer"],
      "timeout_seconds": 30
    }},
    {{
      "step": 2,
      "agent": "retrieval",
      "action": "find_similar_patterns",
      "input_from": "vision",
      "output_to": ["writer"],
      "timeout_seconds": 20
    }}
  ],
  "quality_thresholds": {{
    "min_review_score": 90,
    "max_iterations": 3
  }},
  "parallel_execution": ["step_ids"],
  "estimated_duration_seconds": 120
}}
```
"""


class PromptBuilder:
    """Helper class for dynamic prompt construction"""
    
    @staticmethod
    def add_context_section(base_prompt: str, context: Dict[str, Any]) -> str:
        """Add contextual information to any prompt"""
        if not context:
            return base_prompt
        
        context_section = "\n\n**ADDITIONAL CONTEXT:**\n"
        for key, value in context.items():
            context_section += f"- {key}: {value}\n"
        
        return base_prompt + context_section
    
    @staticmethod
    def add_examples(base_prompt: str, examples: list) -> str:
        """Add few-shot examples to a prompt"""
        if not examples:
            return base_prompt
        
        examples_section = "\n\n**EXAMPLES:**\n"
        for i, example in enumerate(examples, 1):
            examples_section += f"\nExample {i}:\n"
            examples_section += f"Input: {example.get('input', '')}\n"
            examples_section += f"Output: {example.get('output', '')}\n"
        
        return base_prompt + examples_section
    
    @staticmethod
    def format_json_schema(schema: Dict[str, Any]) -> str:
        """Format a JSON schema for inclusion in prompts"""
        import json
        return f"```json\n{json.dumps(schema, indent=2)}\n```"
