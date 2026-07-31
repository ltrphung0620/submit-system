# Requirements extracted from `requirements.pdf`

Reviewed visually and by text extraction on 2026-07-22. Pages 1-4 contain content; page 5 is blank.

## Confirmed requirements

| ID | Page | Confirmed content |
|---|---:|---|
| PDF-01 | 1 | A shared submission system serves five team members. |
| PDF-02 | 1 | A public/network API accepts results sent from members' local machines. |
| PDF-03 | 1 | The UI is readable and supports checking and editing results. |
| PDF-04 | 1 | New results update the open UI in realtime and retain the submitter. |
| PDF-05 | 1 | The system can receive base64-encoded images for inspection. |
| PDF-06 | 1 | A query ZIP can be uploaded and creates UI rows containing STT, File, Query, Result, Image, Note, and potentially more fields. |
| PDF-07 | 1 | KIS, QA, and TRAKE results must be checked against organizer formats. The actual organizer output schemas are not present in the PDF. |
| PDF-08 | 1 | A query may have multiple candidates. Earlier arrivals appear before later, lower-priority arrivals. Individual candidates can be created, edited, and deleted. |
| PDF-09 | 2 | A query's final result is converted to CSV with Vietnamese-safe encoding. CSV files are packed as `<name>.zip/submission/<*.csv>`. |
| PDF-10 | 2 | The PDF links to the HCMC AI Challenge 2025 Group A Codabench competition for output format details. |
| PDF-11 | 2 | KIS input has `file_name`, integer-like frame `img_id`, `video_id`, and `submitter`. |
| PDF-12 | 3 | QA input adds `answer` to `file_name`, frame `img_id`, `video_id`, and `submitter`. |
| PDF-13 | 3-4 | TRAKE input uses an `img_id` array with non-fixed length plus `file_name`, `video_id`, and `submitter`. |
| PDF-14 | 4 | Suggested UI columns are STT, File, Query, Answer, Image, Note; the example shows multiple KIS candidates in priority order, QA answer text, a TRAKE frame sequence, image collection, and submitter note. |

## Syntax-normalized examples

The PDF examples use typographic quotes and omit quotes around some string values. The following are JSON syntax normalizations only; they do not add business meaning.

```json
{"file_name":"query-p1-1-kis","img_id":24834,"video_id":"L21_V001","submitter":"Định"}
```

```json
{"file_name":"query-p1-2-qa","img_id":24834,"video_id":"L21_V001","answer":"Bình Định","submitter":"Định"}
```

```json
{"file_name":"query-p1-3-trake","img_id":[24834,25230,25432],"video_id":"L21_V001","submitter":"Định"}
```

## External URL

PDF page 2 links to `https://www.codabench.org/competitions/10187/#/pages-tab` (the original hyperlink also contains a Facebook tracking query string). On 2026-07-22 the public response identified “HCMC AI Challenge 2025 (Group A)” but exposed no competition page content or output rules. No official CSV rule was therefore extracted.

