# Delivery plan

| Milestone | Scope | Validation |
|---|---|---|
| 1. Source analysis | Visual/text PDF review, external URL attempt, traceability, decisions and blockers | COMPLETE - pages 1-5 reviewed |
| 2. Environment | Backend/frontend skeleton, SQL Server, migration, health, Compose, CI | COMPLETE - Compose configuration updated for SQL Server |
| 3. Query import | Models, safe ZIP parser, synthetic fixture, import API | COMPLETE - unit/integration pass |
| 4. Results | Strict KIS/QA/TRAKE, atomic order, CRUD, images, auth, audit | COMPLETE - integration and 50-request concurrency pass |
| 5. Realtime | Versioned WebSocket events and reconnect/refetch client | COMPLETE - backend and reducer/E2E pass |
| 6. UI | Query table, filters, candidate forms, images, validation/status UX | COMPLETE - Vitest/build/Playwright pass |
| 7. Export | Preview adapters/ZIP/self-validation and fail-closed official endpoint | COMPLETE for preview; official mode blocked by missing spec |
| 8. Release audit | clean start, audits, docs, traceability and report | COMPLETE - no known Python/npm vulnerabilities |
