# Requirements traceability

Status is conservative until the referenced automated command has run successfully.

| Requirement ID | Nội dung yêu cầu | Nguồn và số trang | Mức độ rõ ràng | Thành phần triển khai | Test kiểm chứng | Trạng thái | Ghi chú hoặc blocker |
|---|---|---|---|---|---|---|---|
| R-01 | Shared system for five members and submitter attribution | PDF p1 | Clear | auth/result model/UI | integration auth/result tests | TESTED | API-key mechanism is an implementation decision |
| R-02 | Public/network result API | PDF p1 | Clear | FastAPI `/api/v1/submissions` (`/results` compatibility alias) | API integration + OpenAPI tests | TESTED | New file names auto-create UI groups; deployment exposure is operator-controlled |
| R-03 | Readable UI; inspect/edit/delete/add candidates | PDF p1,p4 | Clear | React query table and dialogs | frontend + E2E | TESTED | |
| R-04 | Realtime create/update/delete without reload | PDF p1 | Clear | WebSocket manager/client | realtime + E2E | TESTED | Single API instance topology |
| R-05 | Optional base64 image inspection | PDF p1 | Partial | image decoder/storage/endpoint/modal | image unit/integration/frontend tests | TESTED | Field name not specified |
| R-06 | Upload query ZIP and display rows/content | PDF p1 | Partial | optional safe importer that enriches canonical API groups | import integration tests | TESTED | Archive details assumed |
| R-07 | KIS/QA/TRAKE checking | PDF p1-4 | Partial | structural validators + dual statuses | validator/API tests | TESTED | Structural validation tested; official rules remain blocked in R-13 |
| R-08 | Multiple ordered candidates; CRUD | PDF p1,p4 | Clear | global `file_name` grouping, atomic sequence, soft delete, versioning | integration/concurrency/E2E | TESTED | Arrival sequence remains backend-authoritative |
| R-09 | KIS payload fields and shape | PDF p2 | Clear | KIS validator/API | KIS tests | TESTED | Numeric domain not specified |
| R-10 | QA payload fields and shape | PDF p3 | Clear | QA validator/API | QA Unicode tests | TESTED | Max answer length not specified |
| R-11 | TRAKE variable frame array payload | PDF p3-4 | Clear structurally | TRAKE validator/API | TRAKE tests | TESTED | Official order/count unknown |
| R-12 | Vietnamese-safe CSV and `submission/*.csv` ZIP | PDF p2 | Partial | operational history CSV plus separate preview exporters/ZIP builder | export round-trip tests | TESTED | History CSV is internal; preview is unverified |
| R-13 | Official per-type CSV compatibility | PDF p1,p2,p4 external link | Blocked | fail-closed official provider | HTTP 409 test | BLOCKED_BY_MISSING_SPEC | See `BLOCKERS.md` |
| R-14 | Suggested STT/File/Query/Answer/Image/Note layout | PDF p4 | Clear | responsive table/cards | frontend/E2E | TESTED | Submitter shown with note metadata |
| R-15 | API/database/migrations/Docker/tests/operations | User delivery brief | Clear | full repository | quality gates | TESTED | Clean-start and security audits pass |

## Summary

- Total: 15
- TESTED: 14
- BLOCKED_BY_MISSING_SPEC: 1
- NOT_STARTED: 0
- IMPLEMENTED without test: 0
- NOT_APPLICABLE: 0
