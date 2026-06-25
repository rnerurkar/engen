# greeting-service — Brownfield Microservices reference (Angular + Spring Boot on ECS Fargate)

This is the **microservices archetype** reference for SDLC Accelerators (developer guide §3).
Unlike the modernization archetype (CSA→TSA), there is **no Integration Inventory and no migration
phases** — the platform team already shipped the infrastructure and boilerplate (Terraform for ECS
Fargate + Oracle RDS + ALB + VPC, Dockerfiles, Jenkins + Harness pipelines). What was missing is a
working "Hello World" that proves every layer wires together.

SDLC Accelerators is initialized in the **existing** repo and generates **application code only** —
it does not generate new Terraform or modify connection settings.

```
specify init --preset sdlc-accelerators-microservice
/specify        # describe the Hello World (see spec.md)
/accelerator.generate   # generate Spring Boot + Angular + Flyway app code into the existing repo
```
