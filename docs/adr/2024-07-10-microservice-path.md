# ADR: Microservice Readiness Path

## Context
Accelerate time-to-market while preserving ability to split into services

## Enforced Constraints:
1. All cross-service calls use gRPC+Protobuf
2. No direct DB access from orchestration layer
3. Event schemas versioned with compatibility guarantees 