"""
tests/test_session_logger.py
--------------------------------
Test M3 (data/session_logger.py) - pure logic, ghi CSV that vao recordings/
roi doc lai kiem tra cot + noi dung. An danh: chi patient_id, khong ten that.

Chay: python tests/test_session_logger.py
"""

import sys
import os
import csv
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.session_logger import SessionLogger, TIMESERIES_FIELDS, EVENT_FIELDS


def main():
    print("=== Test SessionLogger ===\n")
    patient_id = "test1234"
    logger = SessionLogger(patient_id)

    print(f"[1] File duoc tao:\n  {logger.timeseries_path}\n  {logger.events_path}")
    assert patient_id in os.path.basename(logger.timeseries_path)
    assert "test1234" == patient_id and "Nguyen" not in logger.timeseries_path  # khong lan ten that

    logger.log_sample(0.0, "WARMUP", 95.0, 140.0, 165.0, 2, None, "warmup", False)
    logger.log_sample(1.0, "WARMUP", 96.5, 140.0, 165.0, 2, 62.0, "warmup", False)
    logger.log_event(0.0, "phase_changed", {"phase": "WARMUP"})
    logger.log_event(300.0, "phase_changed", {"phase": "MAIN"})
    logger.log_event(305.0, "level_changed", {"level": 7, "reason": "fuzzy", "error": 4.2})
    logger.log_event(310.0, "manual_override", {"expected": 7, "actual": 9})

    summary_path = logger.finalize({"hrr1": 18.5, "time_in_zone_pct": 82.3})
    print(f"[2] Summary: {summary_path}")

    print("[3] Doc lai timeseries.csv...")
    with open(logger.timeseries_path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == TIMESERIES_FIELDS, f"Header sai: {rows[0]}"
    assert len(rows) == 3, f"Ky vong 1 header + 2 dong du lieu, duoc {len(rows)}"
    assert rows[1][1] == "WARMUP" and rows[1][2] == "95.0"
    print(f"  Header: {rows[0]}")
    print(f"  Dong 1: {rows[1]}")

    print("[4] Doc lai events.csv...")
    with open(logger.events_path, encoding="utf-8") as f:
        ev_rows = list(csv.reader(f))
    assert ev_rows[0] == EVENT_FIELDS
    assert len(ev_rows) == 5, f"Ky vong 1 header + 4 event, duoc {len(ev_rows)}"
    override_row = ev_rows[4]
    assert override_row[1] == "manual_override"
    detail = json.loads(override_row[2])
    assert detail["expected"] == 7 and detail["actual"] == 9
    print(f"  Header: {ev_rows[0]}")
    print(f"  manual_override event: {override_row}")

    print("[5] Doc lai summary.json...")
    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)
    assert summary["patient_id"] == patient_id
    assert summary["hrr1"] == 18.5
    print(f"  {summary}")

    # Don dep file test tao ra (khong phai du lieu that cua doi tuong)
    for p in (logger.timeseries_path, logger.events_path, str(summary_path)):
        os.remove(p)

    print("\nOK - SessionLogger ghi/doc CSV + summary dung, an danh (chi patient_id)")


if __name__ == "__main__":
    main()
