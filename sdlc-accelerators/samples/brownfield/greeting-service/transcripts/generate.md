# Transcript — `/accelerator.generate` (greeting-service)

```
You: /accelerator.generate
Agent: Microservice archetype — generating application code only (infra is EXISTING).
Agent:   • Spring Boot: GreetingController, GreetingService, GreetingRepository, Greeting entity
Agent:   • Flyway: V1__create_greeting.sql (table + seed data)
Agent:   • Angular: greeting form + auto-refreshing list (Angular Material), greeting.service.ts
Agent:   • Reused EXISTING application.yml datasource — no DB/connection changes
Agent: Done. No Terraform changed. Open a PR → Jenkins (TF unchanged) + Harness (ECS blue-green).
```

**Generated structure (only app code; existing infra untouched):**

```
existing-spa-pattern/
├── terraform/                       # EXISTING — untouched
├── boilerplate/                     # EXISTING — datasource reused
├── ci-cd/                           # EXISTING — Jenkins + Harness
├── backend/src/main/java/com/company/greeting/
│   ├── GreetingController.java      # GET/POST /api/greetings, /api/health   # GENERATED
│   ├── GreetingService.java         # GENERATED
│   ├── GreetingRepository.java      # GENERATED
│   └── Greeting.java                # JPA entity                              # GENERATED
├── backend/src/main/resources/db/migration/
│   └── V1__create_greeting.sql      # table + seed                           # GENERATED
└── frontend/src/app/greetings/
    ├── greetings.component.ts        # form + list (Angular Material)         # GENERATED
    ├── greetings.component.html      # GENERATED
    └── greeting.service.ts           # calls /api/greetings via nginx/ALB     # GENERATED
```

**Local smoke test:** start Oracle XE → run backend (local profile) → `npm start` frontend
(proxies `/api` to `localhost:8080`) → open `http://localhost:4200`, submit a greeting, see it listed.
