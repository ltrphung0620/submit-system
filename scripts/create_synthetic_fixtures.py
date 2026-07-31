from __future__ import annotations

import base64
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "test-fixtures"
FIXTURES.mkdir(exist_ok=True)

queries = {
    "queries/query-p1-1-kis.txt": "Tìm khung hình có chiếc xe buýt màu xanh.",
    "queries/query-p1-2-qa.txt": "Địa danh trong ảnh thuộc tỉnh nào?",
    "queries/query-p1-3-trake.txt": "Theo dõi ba sự kiện theo thứ tự thời gian.",
}
with zipfile.ZipFile(FIXTURES / "synthetic-query-pack.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for name, content in queries.items():
        archive.writestr(name, content.encode("utf-8"))

# A 1x1 safe PNG used only for implementation tests.
png = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
(FIXTURES / "synthetic-image.png").write_bytes(png)
print("Created synthetic-query-pack.zip and synthetic-image.png")

