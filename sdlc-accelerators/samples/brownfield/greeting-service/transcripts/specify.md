# Transcript — `/specify` (greeting-service)

```
cd existing-spa-pattern
specify init --preset sdlc-accelerators-microservice
# adds .specify/ alongside existing terraform/, boilerplate/, ci-cd/ — modifies nothing

You: /specify
Agent: Microservice template loaded. Fill in Service Purpose, API Contracts, Dependencies,
       Data Model, Frontend Requirements, Infrastructure Requirements.
You: (pastes the Hello World greeting spec — see spec.md)
Agent: Spec captured. Note: Infrastructure Requirements = EXISTING. I will generate application
       code only and reuse the datasource in boilerplate/backend/.../application.yml.
       No Terraform will be generated or modified.
```
