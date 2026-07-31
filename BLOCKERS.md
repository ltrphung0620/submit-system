# Blockers

## P0 - Official submission format is not verifiable

- **Source:** `docs/requirements.pdf`, pages 2 and 4, points to `https://www.codabench.org/competitions/10187/#/pages-tab` instead of embedding the rules.
- **Access result (2026-07-22):** the public page identifies the competition but its dynamic rules/content were not returned; the interactive in-app browser was unavailable. No authenticated fixture or organizer document exists in the repository.
- **Missing:** per-type CSV schemas, headers, column order, delimiter/quoting, byte encoding/BOM, filenames, row limits, candidate selection policy, and complete archive entry list.
- **Impact:** official CSV adapters cannot be configured or golden-tested; Codabench compatibility cannot be claimed.
- **Implemented behavior:** preview export remains available and is visibly marked `UNVERIFIED`; official export returns HTTP 409 with `OFFICIAL_FORMAT_NOT_VERIFIED`.
- **Question:** Please provide an accessible organizer rules document or a known-accepted submission ZIP and confirm the candidate selection policy.

This blocker does not prevent query import, structural validation, CRUD, images, realtime UI, or preview export.

