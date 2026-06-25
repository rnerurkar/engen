# Microservice Spec — Greeting Service (Hello World reference)

## Service Purpose
Hello World reference implementation for the Angular + Spring Boot SPA pattern on ECS Fargate with
Oracle RDS. This is NOT a production application — it is a minimal working example that proves every
layer of the stack works end to end.

## API Contracts
- `GET  /api/greetings`        — list all greetings
- `POST /api/greetings`        — create a greeting (body: `{ "name": "Alice", "message": "Hello" }`)
- `GET  /api/greetings/{id}`   — get greeting by ID
- `GET  /api/health`           — health check (returns DB connectivity status)

## Dependencies
Oracle RDS — **EXISTING** database at the endpoint configured in
`boilerplate/backend/src/main/resources/application.yml`. The agent MUST use the EXISTING datasource
configuration. DO NOT create a new database or modify the connection settings.

## Data Model
`Greeting`: id (NUMBER, auto-generated), name (VARCHAR2 100), message (VARCHAR2 500),
created_at (TIMESTAMP, auto-generated)

## Frontend Requirements
Angular SPA with one page:
- A form with "Name" and "Message" fields + Submit button
- A list below showing all submitted greetings (auto-refreshes)
- Minimal styling using Angular Material
- Calls backend via `/api/greetings` (proxied through nginx/ALB)

## Infrastructure Requirements
**EXISTING** infrastructure — DO NOT generate new Terraform. Use the existing ECS Fargate + Oracle
RDS + ALB from `terraform/`. Use the existing Dockerfiles from `boilerplate/`. Use the existing
CI/CD from `ci-cd/`. Only generate application code that runs inside the existing containers.

## Non-Functional Requirements
- Auth: none for this reference (internal demo); inherits ALB + VPC controls
- Observability: CloudWatch logs (existing log groups); health endpoint reports DB connectivity
- DB migrations: Flyway (one table + seed data)
