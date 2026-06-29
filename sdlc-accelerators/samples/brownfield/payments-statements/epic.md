# Rally Epic E6105 — a payments and statements application on WebSphere 9

*Archetype: brownfield. ObjectVersion 9 · LastUpdate 2026-06-21.*

## Description
a payments and statements application on WebSphere 9. all three integrations are in scope. JAX-RS on WebSphere 9. sync api. read-only. high. dual-read. OpenAPI 3.0 documented. stateless. 3M calls/day p95 < 300ms. Spring Boot API on ECS. Batch renderer on WebSphere 9. batch. write-only. medium. dual-write. internal jobs. stateless. nightly 2M statements batch SLA 6h. AWS Batch on Fargate. Apigee client v1 cross-cloud. async messaging. write-only. critical. dual-write. message contract documented. stateless. 900K postings/day. AWS SQS + Apigee cross-cloud.

## Non-Functional Requirements
- recovery point objective of 5 minutes and recovery time objective of 30 minutes
