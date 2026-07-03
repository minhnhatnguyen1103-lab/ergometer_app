"""
data/pending_session_store.py
--------------------------------
Luu/liet ke/xoa cac session dang do (da co PatientProfile + HR_rest,
nhung chua chay duoc MICT vi Arduino chua ket noi). Moi patient 1 file
JSON rieng trong data/pending_sessions/.

KHONG phai noi luu ket qua chinh thuc (final_group) - do la viec cua
session_logger.py sau nay. Day chi la "cho tam" de khong phai do lai
HR_rest tu dau moi lan Arduino chua san sang.
"""

import os
import json
import glob

from data.patient import PatientProfile

PENDING_DIR = os.path.join(os.getcwd(), "data", "pending_sessions")


def save_pending(patient: PatientProfile) -> str:
    os.makedirs(PENDING_DIR, exist_ok=True)
    path = os.path.join(PENDING_DIR, f"{patient.patient_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(patient.to_raw_dict(), f, ensure_ascii=False, indent=2)
    return path


def list_pending() -> list[dict]:
    """Tra ve danh sach tom tat (khong load full PatientProfile) de hien len UI."""
    if not os.path.isdir(PENDING_DIR):
        return []
    out = []
    for fp in sorted(glob.glob(os.path.join(PENDING_DIR, "*.json"))):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
            out.append({
                "patient_id": d["patient_id"],
                "name": d["name"],
                "created_at": d["created_at"],
                "path": fp,
            })
        except Exception:
            continue
    return out


def load_pending(patient_id: str) -> PatientProfile | None:
    path = os.path.join(PENDING_DIR, f"{patient_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return PatientProfile.from_raw_dict(d)


def delete_pending(patient_id: str) -> None:
    path = os.path.join(PENDING_DIR, f"{patient_id}.json")
    if os.path.exists(path):
        os.remove(path)
