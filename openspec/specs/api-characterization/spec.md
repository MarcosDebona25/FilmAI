# API characterization capability

## Purpose

Freeze the API responses observed before the multilingual error contract is
implemented, so subsequent work can identify deliberate changes and regressions.

## Requirements

### Requirement: Capture actual production responses

Each characterization scenario MUST execute an existing endpoint, serializer,
validator or exception handler and compare its HTTP status and complete JSON body
with a versioned reference. References MUST NOT contain invented response text.

#### Scenario: Current error contract remains unchanged

- GIVEN a scenario in `backend/filmai/tests_contrato.py`
- WHEN the scenario executes with `DEBUG=False` and `es-ar` active
- THEN its status and JSON body match `backend/filmai/tests_golden/api/`

#### Scenario: Explicit regeneration

- GIVEN the reference suite is run normally
- THEN it reads references without updating them
- WHEN `REGENERAR_REFERENCIAS_API=1` is explicitly supplied
- THEN references are regenerated from the executed responses

### Requirement: Distinguish public responses from defensive branches

The inventory MUST document directly invoked defensive validators separately
from HTTP scenarios. External integrations MAY be isolated at their transport
or OAuth boundary, preserving production validation and response rendering.

#### Scenario: Sensitive and variable inputs stay out of references

- GIVEN an invalid confirmation, reset or authentication scenario
- WHEN a token or date is required to reach the branch
- THEN the reference stores only the response status and body
- AND variable input tokens, timestamps and database identifiers are omitted
