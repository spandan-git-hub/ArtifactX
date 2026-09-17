# R1 — AI Excision and Zero-Local-Storage Hardening

## Objective

Remove the experimental AI copilot/sentiment subsystem and harden evidence handling so the repository no longer depends on local evidence/report storage.

The source roadmap identifies R1 as:
- remove backend assistant router/service;
- remove frontend assistant drawer/hook/service;
- remove AI UI triggers;
- enforce database-backed evidence and in-memory streams.

## Surgical edit plan

### Delete
- `backend/api/assistant.py`
- `backend/services/assistant_service.py`
- `frontend/src/components/assistant/ForensicAssistantDrawer.jsx`
- `frontend/src/hooks/useAiAssistant.js`
- `frontend/src/services/assistantService.js`

### Edit
- `backend/app/main.py`: remove assistant router import/include.
- `frontend/src/pages/CaseWorkspacePage.jsx`: remove copilot controls/drawer.
- `frontend/src/pages/ChatViewerPage.jsx`: remove copilot controls.
- any route/service/index exports referencing assistant modules.
- report code: verify no assistant fields are read.
- package manifests: remove assistant-only dependencies if any.

### Search requirement
Run a repository-wide search for:
`assistant`, `copilot`, `sentiment`, `suspicion`, `tone`, `useAiAssistant`.

Do not delete unrelated words merely because they contain a substring.

## Zero-local-storage edits

Refactor:
- `backend/utils/file_storage.py`
- evidence upload service;
- ZIP extraction;
- report generation;
- media derivation;
- parser handoff.

Replace persistent local paths with:
- database blobs;
- in-memory streams;
- derived artifact records.

## Acceptance tests

- Backend imports successfully.
- Frontend production build succeeds.
- No assistant route appears in OpenAPI.
- No assistant UI appears.
- No assistant module import remains.
- Court reports contain no AI-derived fields.
- Evidence upload writes zero files to `uploads/`.
- Report generation writes zero files to `reports/`.
- Existing deterministic functionality remains operational.
- Existing Phase 14 regression tests are adapted to the new storage invariant.

## Completion evidence

Record:
- commit/change identifier;
- tests executed;
- zero-disk assertion;
- repository search result showing no active assistant references;
- migration status.

Do not mark R1 complete on build success alone.
