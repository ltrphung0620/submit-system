# Open questions

| Priority | Question | Impact | Proposed configurable default |
|---|---|---|---|
| P0 | Does an organizer-accepted fixture confirm the user-provided headerless KIS, QA, and TRAKE row layouts? | Official export correctness | Preview implements the supplied rows; official mode remains disabled |
| P0 | Does the organizer require UTF-8 BOM or plain UTF-8? | Byte compatibility and Vietnamese text | Preview keeps UTF-8 BOM for Vietnamese-safe opening |
| P0 | What exact CSV filename mapping and per-query row limit apply? | Archive acceptance | Preview sanitizes `file_name` to `<file_name>.csv` with no artificial row cap |
| P0 | Which candidate(s) form the “final result”: first, selected, or all? | Submission semantics | Preview includes all active valid candidates by `arrival_seq` |
| P0 | Are there archive entries beyond `submission/*.csv`? | Archive acceptance | Preview contains only CSVs under `submission/` |
| P1 | What are official `video_id`, `img_id`, QA length, and TRAKE count/order rules? | Official validation | Structural safety checks only |
| P1 | What exact query ZIP layout and encoding are official? | Import compatibility | Recursive `.txt`, strict UTF-8/BOM |
| P1 | May TRAKE span several videos? | API/data model | Current payload follows the PDF's single `video_id` |
| P1 | Should duplicate candidates or retries be deduplicated? | Duplicate results | No semantic deduplication |
| P2 | May one candidate contain multiple images, and are images part of the submission ZIP? | Storage/export | One UI-only image; excluded from preview ZIP |
