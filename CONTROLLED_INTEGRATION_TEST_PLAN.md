# FOG-ORCHESTRATOR 2.0 — CONTROLLED INTEGRATION TEST PLAN

**Date**: 2026-08-28  
**Author**: Verification & Validation Lead, Safety-Critical Integration Engineer  
**Scope**: 4-Stage Test Plan for Adapter Unit Tests, Integration Contracts, Sandbox E2E Scenarios, and Full Regression

---

## 1. Test Stage Overview

- **Stage 1: Adapter Unit Tests**: Independent unit testing of all 8 adapter modules in `tests/`.
- **Stage 2: Integration Contract Verification**: 15-check contract verification testing schema compatibility, scaling, unit conversion, and position quality in `verify_integration_contracts.py`.
- **Stage 3: End-to-End Sandbox Testing**: 12-step scenario execution and 10 fault isolation tests (Faults A..J) in `verify_controlled_integration.py`.
- **Stage 4: Master Regression Verification**: Full execution of Phase 1, Phase 2, Adapter, Contract, and Sandbox test suites in `verify_all_regressions.py`.
