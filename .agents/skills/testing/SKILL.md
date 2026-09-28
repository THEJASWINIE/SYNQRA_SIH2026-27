---
name: testing
description: Verification rules for implementing and reviewing FOG-ORCHESTRATOR Task 1 features.
---

# Verification Requirements

Do not claim work is complete without verification.

## For Every Feature

1. Inspect existing code before modification.
2. Identify affected files.
3. Implement only the requested feature.
4. Run linting.
5. Run type checking.
6. Run relevant tests.
7. Start the application.
8. Verify the feature works.
9. Test relevant failure states.
10. Report known limitations.

## HMI-Specific Checks

Where applicable, verify:

- Connected state
- Loading state
- Error state
- Stale data state
- Disconnected state
- Data freshness
- Alert visibility
- Actual versus safe value distinction

## Completion Report

Always report:

- Files changed
- Verification performed
- Test results
- Remaining limitations or risks

Never report a feature as complete merely because code was written.