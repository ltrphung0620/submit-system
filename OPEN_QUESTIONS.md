# Open questions

| Priority | Question | Impact | Proposed configurable default |
|---|---|---|---|
| P0 | What are the exact KIS, QA, and TRAKE CSV columns and column order? | Official export correctness | Official mode disabled |
| P0 | Do CSVs have headers, which delimiter/quoting rules, and UTF-8 or UTF-8 BOM? | Byte compatibility and Vietnamese text | Preview uses header, comma, RFC 4180, UTF-8 |
| P0 | What exact CSV filename mapping and per-query row limit apply? | Archive acceptance | Preview sanitizes `file_name` to `<file_name>.csv` with no artificial row cap |
| P0 | Which candidate(s) form the “final result”: first, selected, or all? | Submission semantics | Preview includes all active valid candidates by `arrival_seq` |
| P0 | Are there archive entries beyond `submission/*.csv`? | Archive acceptance | Preview contains only CSVs under `submission/` |
| P1 | What are official `video_id`, `img_id`, QA length, and TRAKE count/order rules? | Official validation | Structural safety checks only |
| P1 | What exact query ZIP layout and encoding are official? | Import compatibility | Recursive `.txt`, strict UTF-8/BOM |
| P1 | May TRAKE span several videos? | API/data model | Current payload follows the PDF's single `video_id` |
| P1 | Should duplicate candidates or retries be deduplicated? | Duplicate results | No semantic deduplication |
| P1 | What authentication and cross-member edit/delete permissions are intended? | Access control | Configurable API keys; owner-only default |
| P2 | May one candidate contain multiple images, and are images part of the submission ZIP? | Storage/export | One UI-only image; excluded from preview ZIP |

