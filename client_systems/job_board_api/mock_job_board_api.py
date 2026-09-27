"""
Simulated job-board aggregator API (Naukri + Indeed applications for the client's posting).

Behaves like a real third-party API:
  - offset pagination with `total`, `page`, `per_page`, `has_more`
  - page 3 fails once with HTTP 500, page 5 is rate-limited once with HTTP 429 + Retry-After
  - page 4 repeats the last record of page 3 (offset drift while new applications arrive)

Run:  python client_systems/job_board_api/mock_job_board_api.py   (listens on 127.0.0.1:8765)
"""
import json
import os
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
DATA = json.loads((Path(__file__).parent / "applications.json").read_text())
hits: dict[tuple, int] = {}


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "job-board-aggregator"})


@app.get("/v1/postings/CS-AGENT-BLR/applications")
def applications():
    date_from = request.args.get("applied_from", "0000")
    date_to = request.args.get("applied_to", "9999")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 50))))

    key = (date_from, date_to, page)
    hits[key] = hits.get(key, 0) + 1
    if page == 3 and hits[key] == 1:
        return jsonify({"error": "upstream timeout"}), 500
    if page == 5 and hits[key] == 1:
        return jsonify({"error": "rate limit"}), 429, {"Retry-After": "1"}

    rows = [r for r in DATA if date_from <= r["applied_at"][:10] <= date_to]
    start = (page - 1) * per_page
    if page == 4 and start > 0:
        start -= 1                      # offset drift: one record from page 3 comes back again
    chunk = rows[start:(page - 1) * per_page + per_page]
    return jsonify({"data": chunk, "page": page, "per_page": per_page, "total": len(rows),
                    "has_more": (page * per_page) < len(rows)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("JOB_BOARD_PORT", 8765)), debug=False)
