# Overlay Skill — Security

Applies Model Armor callbacks, Agent Identity (least-privilege), VPC-SC, CMEK, Secret Manager
to all generated code. NEVER-SWAPPABLE: Model Armor, Binary Authorization, cosign.

Templates: model_armor.py.j2, agent_identity.py.j2 (in templates/code/<archetype>/).
Driven by: screening_config, agent_identity_config from app-blueprint.json.
