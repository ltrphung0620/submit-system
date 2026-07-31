# Repository working agreement

- `docs/requirements.pdf` is immutable and is the primary product source.
- Do not describe preview CSV output as an official Codabench submission.
- Keep official export fail-closed until every P0 item in `BLOCKERS.md` is resolved.
- Backend changes require `ruff`, `mypy`, and `pytest`; frontend changes require ESLint, TypeScript, Vitest, and a production build.
- Database schema changes must be made through Alembic migrations. The application must not call `create_all` at runtime.
- User content is untrusted: do not render raw HTML, trust uploaded MIME types, log API keys/base64, or use archive paths as filesystem paths.
- Store timestamps in UTC and preserve `arrival_seq` across edits and deletes.
- Synthetic fixtures must be named `synthetic-*`; never label generated data as official.

