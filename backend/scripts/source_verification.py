from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import merge_sources_by_page

srcs = [
    {"doc_id": "konkuk-guide", "page": 23, "evidence": "A"},
    {"doc_id": "konkuk-guide", "page": 21, "evidence": "B"},
    {"doc_id": "konkuk-guide", "page": 23, "evidence": "C"},
    {"doc_id": "konkuk-guide", "page": 23, "evidence": "A"},   # 중복
    {"doc_id": "konkuk-guide", "page": 21},                     # evidence 없음
]
out = merge_sources_by_page(srcs)
assert [s["page"] for s in out] == [23, 21]       # 순서 유지
assert out[0]["evidence"] == "A\n\nC"              # 합치기 + 중복 제거
assert out[1]["evidence"] == "B"                    # 빈 evidence 무시