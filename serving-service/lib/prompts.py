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
        Comprehensive prompt for generating specific documentation sections.
        Dynamically adjusts instructions based on the section type and uses
        the reference content (Donor) as a strict structural template.
        """
        
        # 1. Base identity and core task
        prompt = f"""You are a Senior Technical Writer specializing in software architecture.

**TASK:** Write the '{section_name}' section for a new architecture pattern.

**PROJECT CONTEXT:**
The user is designing a system described as:
"{description}"

**THE GOAL:**
We have retrieved a high-quality "Donor Pattern" (Reference Content) to serve as a style guide. 
Your job is to generate the '{section_name}' for the NEW project, but mimicking the exact **structure, depth, tone, and formatting** of the Reference Content.

---
**REFERENCE CONTENT (DONOR):**
{reference_content}
---
"""

        # 2. Section-Specific Strategy (The "Why" and "How" for each unique section)
        # This provides the unique "angle" request by the user.
        section_strategies = {
            "Problem": """
**STRATEGY FOR 'PROBLEM' SECTION:**
- **Tone:** Empathetic but analytical. Focus on the "pain".
- **Structure:** Start with context/background, move to specific challenges, end with consequences of doing nothing.
- **Key Elements:** Mention specific technical bottlenecks (latency, coupling) and business impacts (cost, time-to-market).
- **Differentiation:** Ensure the problem clearly justifies why a complex pattern is needed.
""",
            "Solution": """
**STRATEGY FOR 'SOLUTION' SECTION:**
- **Tone:** Authoritative and descriptive.
- **Structure:** High-level overview -> Component deep dive -> Interaction flow.
- **Key Elements:** Justify technology choices. Explain *how* it solves the specific problems defined earlier.
- **Visuals:** Refer to standard diagrams (Context, Container) textually.
""",
            "Implementation": """
**STRATEGY FOR 'IMPLEMENTATION' SECTION:**
- **Tone:** Instructional and pragmatic.
- **Structure:** Prerequisites -> Step-by-step logic -> Configuration samples.
- **Key Elements:** Include pseudo-code or configuration snippets. Discuss sequencing (what to build first).
- **Detail Level:** High. This is for the developers building it.
""",
            "Trade-offs": """
**STRATEGY FOR 'TRADE-OFFS' SECTION:**
- **Tone:** Objective and balanced.
- **Structure:** Pros vs. Cons comparison.
- **Key Elements:** Highlight complexity, cost, and operational overhead. Discuss when NOT to use this pattern.
""",
            "Overview": """
**STRATEGY FOR 'OVERVIEW' SECTION:**
- **Tone:** Executive summary style.
- **Structure:** One paragraph summary -> Key capabilities -> Business value.
- **Key Elements:** Be concise. This is the "Hook" for the reader.
"""
        }

        # Inject the specific strategy or a generic fallback
        prompt += section_strategies.get(section_name, "**STRATEGY:** Follow the structure of the reference content precisely.")

        # 3. Handling Critique (Iterative refinement)
        if critique:
            prompt += f"""

**CRITICAL FEEDBACK TO ADDRESS (Previous Draft):**
The previous attempt had issues. You MUST fix these specific points:
{critique}
"""

        # 4. Universal Instructions
        prompt += f"""

**EXECUTION INSTRUCTIONS:**
1. **Analyze the Reference:** Look at the headers, list styles, and paragraph length in the Reference Content above.
2. **Apply to New Context:** Write the content for the *new* project described in "PROJECT CONTEXT", but fit it into the Reference's structure.
3. **Format:** Use Markdown. Do NOT output the "Strategy" text or meta-comments. Just the documentation content.
4. **Consistency:** If the reference uses bold key terms, you use bold key terms. If it uses tables, you use tables.
5. **VISUAL ADAPTATION (CRITICAL):** 
   - The Reference Content may contain image placeholders like `[Image Description: ... | GCS Link: ...]`.
   - If you see such a marker, it means this section REQUIRES a diagram.
   - You must generate a **Mermaid.js** code block (e.g., `mermaid`) representing the equivalent diagram for the NEW project.
   - If a Mermaid diagram is too complex, write a clear placeholder: `> **[Suggested Diagram]:** <Detailed description of what the new image should show>`

**OUTPUT:**
Generate the '{section_name}' markdown content now.
"""
        
        if context:
            prompt += f"\n\n**ADDITIONAL SYSTEM DETAILS:**\n{context}"
        
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
