# app-blueprint.md — Greeting Service (microservices archetype)

> **Archetype:** brownfield-microservices  |  **Lifecycle state:** LIVE  |  Infrastructure is EXISTING — only application code is generated.

## §1 Service Overview
A minimal Angular + Spring Boot "Hello World" that proves the existing ECS Fargate + Oracle RDS + ALB
stack works end to end: form submit → ALB → Spring Boot → Oracle → response → SPA list.

## §2 Tech Stack
| Layer | Tech (all pre-existing infra) |
|---|---|
| Frontend | Angular + Angular Material (nginx container) |
| Backend | Spring Boot (spring-boot-starter-web, spring-data-jpa, ojdbc11) |
| Database | Oracle RDS (existing datasource in `application.yml`) |
| Migrations | Flyway |
| Runtime | ECS Fargate (existing task defs), ALB (existing target groups) |
| Registry | ECR (existing frontend + backend repos) |
| CI/CD | Jenkins (terraform, unchanged) + Harness (ECS blue-green) |

## §3 Component Topology
- Angular SPA → nginx → ALB → Spring Boot REST → Oracle RDS.
- One JPA entity (`Greeting`), one repository, one service, one controller.
- Flyway migration `V1__create_greeting.sql` creates the table + seed rows.

## §4 What is generated vs. what exists
- **Generated:** Spring Boot controller/service/repository/entity, Angular component/service/routing,
  Flyway migration. Nothing else.
- **Existing (untouched):** all Terraform, Dockerfiles, nginx/proxy config, Jenkins + Harness pipelines.

## §5 Validation
Proves: Angular→nginx→ALB→Spring Boot round-trip; Spring Boot→Oracle round-trip; schema management;
full end-to-end form submit → store → retrieve → display.
