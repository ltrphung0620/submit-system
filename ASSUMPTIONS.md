# Assumptions and implementation decisions

These are configurable implementation choices, not official competition rules.

1. **Query sets.** Every ZIP import creates a separate `QuerySet` and atomically makes it active, preventing results from different packs from mixing.
2. **Query archive policy.** Valid query inputs are UTF-8/UTF-8-BOM `.txt` files anywhere in the archive. Directories and non-`.txt` entries are ignored. Basenames without `.txt` are canonical `file_name` values and must be unique case-insensitively.
3. **Type inference.** Case-insensitive `-kis`, `-qa`, and `-trake` suffixes map to canonical types. Other names import as `unknown` and cannot receive a result until corrected by a future administration feature or re-import.
4. **Structural validation.** `img_id` is a strict non-negative integer for KIS/QA and a non-empty array of strict non-negative integers for TRAKE. TRAKE preserves supplied order; official count/order constraints remain unverified. `video_id`, `submitter`, and QA `answer` must contain at least one non-whitespace character; content is otherwise preserved.
5. **Image API.** The optional fields are `image_base64` and `image_mime_type`. Raw base64 and data URLs are accepted. JPEG, PNG, and WebP are allowed; detected magic bytes are authoritative. One attachment per candidate is currently supported.
6. **Authentication.** `AUTH_MODE=disabled` is allowed for development/test. Production examples use `AUTH_MODE=api_key`, `X-API-Key`, and a configured key-to-submitter map. This security layer is not specified by the PDF.
7. **Mutation permission.** `PERMISSION_MODE=owner_only` is the safe default. `all_members` is available. API-key body submitter mismatch is forbidden.
8. **Realtime topology.** The default deployment runs one API instance and broadcasts WebSocket events in-process. Multiple API replicas require an external pub/sub adapter and are outside the default Compose topology.
9. **Priority and preview selection.** `arrival_seq` is immutable per query. Active `priority` is mutable, scoped per query, and compacted to `1..N` after deletion. Preview export writes every active structurally valid candidate in priority order. This is not an official selection policy.
10. **Preview CSV.** Preview files use UTF-8, RFC 4180 CSV behavior, CRLF line endings, a header, and internal columns `file_name,query_type,priority,video_id,img_id,answer,submitter`. This is explicitly not the organizer format.
11. **Idempotency.** Client retry idempotency is not enabled because no key contract is specified. Atomic `arrival_seq` prevents ordering collisions, not duplicate semantic submissions.
