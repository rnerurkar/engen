# Overlay Skill — Observability

OTel spans per agent, Cloud Monitoring/Logging/Trace (GCP defaults), optional Dynatrace+Splunk.
Driven by: observability_config from app-blueprint.json.
Every agent invocation is span-wrapped (see agent templates' _tracer usage).
