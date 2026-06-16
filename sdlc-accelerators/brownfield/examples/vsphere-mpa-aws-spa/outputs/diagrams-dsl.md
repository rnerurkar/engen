## component-end-state
```
// Component (end-state TSA)
INT-001 [label: "aws-cloudfront+aws-s3+spa"]
INT-002 [label: "spring-boot+ecs-fargate"]
INT-003 [label: "apigee+privatelink+psc"]
INT-004 [label: "aws-sqs+aws-sdk-v2"]
```

## sequence-end-state
```
// Sequence (end-state)
Client -> INT-001: UI rendering
Client -> INT-002: Server-side application logic
Client -> INT-003: Domain API consumption
Client -> INT-004: Async messaging
```

## sequence-transition
```
// Sequence (transition: dual-write windows, strangler routes, cutover gates)
Phase0 -> INT-003: blue-green (14-day soak)
Phase1 -> INT-003: blue-green (14-day soak)
Phase2 -> INT-001: big-bang (N/A (paired with INT-002))
Phase2 -> INT-002: strangler-fig (feature-flag dual-read during soak)
Phase2 -> INT-004: dual-publish (48h dual-publish)
```

## infrastructure
```
// Infrastructure (AWS account, VPC, region, cross-cloud links)
INT-003: cross-cloud link (privatelink+psc)
```