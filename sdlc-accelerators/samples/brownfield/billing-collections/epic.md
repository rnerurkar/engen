# Rally Epic E6101 — a legacy billing and collections monolith on WebLogic 12

*Archetype: brownfield. ObjectVersion 12 · LastUpdate 2026-06-21.*

## Description
a legacy billing and collections monolith on WebLogic 12. all three integrations are in scope this iteration. JSF on WebLogic 12. sync api. bidirectional. high. hard-cutover. internal pages. session sticky. 1.5M page views/day p95 < 700ms. React SPA on CloudFront. Spring Batch 4 on WebLogic 12. batch. read-only. critical. dual-read. internal jobs. stateless. nightly 3M accounts batch SLA 4h. AWS Batch on Fargate. IBM MQ 9.1 producer. async messaging. write-only. high. dual-write. message contract documented. stateless. 400K payments/day. AWS SQS producer.

## Non-Functional Requirements
- exit the on-prem datacenter by Q4
