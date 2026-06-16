# Brownfield Migration Blueprint (TSA)

**Migration readiness score:** 100/100

## Integration Migration Blocks

### INT-001 — UI rendering
- R-factor: refactor
- Substitution: ['jsp', 'tomcat'] → ['aws-cloudfront', 'aws-s3', 'spa']
- Pattern: PAT-T-001-bigbang-ui (confidence 0.9)
- Transition: PAT-T-001-bigbang-ui; cutover big-bang
- Attested ADRs: none
- Rollback: CloudFront origin failback to Tomcat; rollback SLA 15 min

### INT-002 — Server-side application logic
- R-factor: refactor
- Substitution: ['tomcat', 'servlet'] → ['spring-boot', 'ecs-fargate']
- Pattern: PAT-T-004-strangler-bff (confidence 0.9)
- Transition: PAT-T-004-strangler-bff; cutover strangler-fig
- Attested ADRs: none
- Rollback: feature-flag flip to Tomcat path; rollback SLA 5 min (critical)

### INT-003 — Domain API consumption
- R-factor: replatform
- Substitution: ['ibm-api-connect', 'apic'] → ['apigee', 'privatelink', 'psc']
- Pattern: PAT-T-009-bluegreen-gateway (confidence 0.9)
- Transition: PAT-T-009-bluegreen-gateway; cutover blue-green
- Attested ADRs: none
- Rollback: gateway route flip APIC↔Apigee; rollback SLA 10 min

### INT-004 — Async messaging
- R-factor: refactor
- Substitution: ['ibm-mq', 'spring-jms'] → ['aws-sqs', 'aws-sdk-v2']
- Pattern: PAT-T-007-dual-publish-mq-sqs (confidence 0.9)
- Transition: PAT-T-007-dual-publish-mq-sqs; cutover dual-publish
- Attested ADRs: none
- Rollback: disable SQS publish, MQ remains source of truth; rollback SLA 5 min
