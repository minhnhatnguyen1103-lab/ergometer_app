"""
tests/test_fuzzy_controller.py
----------------------------------
Test M1 (control/fuzzy_controller.py) - pure logic, khong can UI/hardware.

Kiem tra:
  1. Ca 15 o bang luat (dung diem dinh/vung bao hoa cua tung tap mo de dam
     bao chi 1 tap co muc do thanh vien = 1, output khong bi lan giua cac o).
  2. Vung chet cung (deadband) ep delta_level = 0.
  3. Hard clamp bien level 1 va 16.
  4. Co canh bao out_of_range dung khi new_level ngoai [5,10].

Chay: python tests/test_fuzzy_controller.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control.fuzzy_controller import FuzzyController

HR_TARGET_CENTER = 150.0
DT = 6.0  # giay - trong khoang FUZZY_UPDATE_INTERVAL_SEC_MIN..MAX (5-8s)

# Diem "dinh"/vung bao hoa cho tung nhan - chon de muc do thanh vien = 1
# roi rac (khong lan sang tap ben canh), khop dung 15 o bang luat.
E_POINTS = {"NB": -25.0, "NS": -8.0, "ZE": 0.0, "PS": 8.0, "PB": 25.0}
DE_POINTS = {"RISE": 6.0, "STEADY": 0.0, "FALL": -6.0}

EXPECTED_OUT_LABEL = {
    ("NB", "RISE"): "NB", ("NB", "STEADY"): "NB", ("NB", "FALL"): "NS",
    ("NS", "RISE"): "NS", ("NS", "STEADY"): "NS", ("NS", "FALL"): "ZE",
    ("ZE", "RISE"): "NS", ("ZE", "STEADY"): "ZE", ("ZE", "FALL"): "PS",
    ("PS", "RISE"): "ZE", ("PS", "STEADY"): "PS", ("PS", "FALL"): "PS",
    ("PB", "RISE"): "PS", ("PB", "STEADY"): "PB", ("PB", "FALL"): "PB",
}


def _hr_actual_prev_for(e_label: str, de_label: str):
    e = E_POINTS[e_label]
    de = DE_POINTS[de_label]
    hr_actual = HR_TARGET_CENTER - e
    hr_prev = hr_actual - de * DT
    return hr_actual, hr_prev


def test_15_rule_cells():
    print("=== [1] Kiem tra 15 o bang luat ===")
    fc = FuzzyController()
    n_checked = 0
    for (e_label, de_label), out_label in EXPECTED_OUT_LABEL.items():
        expected_delta = fc.OUT_LABEL_TO_INT[out_label]
        hr_actual, hr_prev = _hr_actual_prev_for(e_label, de_label)
        result = fc.compute(
            hr_actual=hr_actual, hr_target_center=HR_TARGET_CENTER,
            hr_prev=hr_prev, dt=DT, current_level=8,
        )
        # O (ZE, STEADY) trung voi vung chet cung (|e|=0<=3, |de|=0<=2) - ca
        # 2 co che (fuzzy thuan tuy va deadband) deu phai cho ra 0, nen van
        # kiem duoc binh thuong.
        assert result.delta_level == expected_delta, (
            f"O ({e_label},{de_label}): ky vong delta={expected_delta} "
            f"({out_label}), duoc {result.delta_level} (crisp={result.crisp_output:.3f})"
        )
        n_checked += 1
        print(f"  ({e_label:>2},{de_label:>7}) -> delta={result.delta_level:+d}  OK")
    assert n_checked == 15, f"Phai kiem tra dung 15 o, moi kiem {n_checked}"
    print(f"OK - toan bo {n_checked} o bang luat dung nhu thiet ke\n")


def test_deadband():
    print("=== [2] Kiem tra vung chet cung (deadband) ===")
    fc = FuzzyController()
    # |e|=1 <= HR_DEADBAND_BPM(3), |de| nho -> phai ep delta=0 du fuzzy tho co the khac 0
    hr_actual = HR_TARGET_CENTER - 1.0
    hr_prev = hr_actual - 0.5 * DT
    result = fc.compute(hr_actual, HR_TARGET_CENTER, hr_prev, DT, current_level=7)
    assert result.delta_level == 0, f"Deadband phai ep delta=0, duoc {result.delta_level}"
    print(f"  e=1, de=0.5 -> delta=0 (crisp tho={result.crisp_output:.3f}) OK\n")


def test_clamp_bien():
    print("=== [3] Kiem tra hard clamp bien level 1 va 16 ===")
    fc = FuzzyController()

    # HR rat thap hon target -> delta ky vong +2, nhung current_level=16 -> phai giu 16
    hr_actual, hr_prev = _hr_actual_prev_for("PB", "STEADY")
    result = fc.compute(hr_actual, HR_TARGET_CENTER, hr_prev, DT, current_level=16)
    assert result.delta_level == 2
    assert result.new_level == 16, f"Phai clamp ve 16, duoc {result.new_level}"
    print(f"  current=16, delta=+2 -> new_level={result.new_level} (clamp dung) OK")

    # HR rat cao hon target -> delta ky vong -2, current_level=1 -> phai giu 1
    hr_actual, hr_prev = _hr_actual_prev_for("NB", "STEADY")
    result = fc.compute(hr_actual, HR_TARGET_CENTER, hr_prev, DT, current_level=1)
    assert result.delta_level == -2
    assert result.new_level == 1, f"Phai clamp ve 1, duoc {result.new_level}"
    print(f"  current=1, delta=-2 -> new_level={result.new_level} (clamp dung) OK\n")


def test_out_of_range_warning():
    print("=== [4] Kiem tra canh bao out_of_range [5,10] ===")
    fc = FuzzyController()

    hr_actual, hr_prev = _hr_actual_prev_for("ZE", "STEADY")
    result = fc.compute(hr_actual, HR_TARGET_CENTER, hr_prev, DT, current_level=3)
    assert result.new_level == 3
    assert result.out_of_range is True, "level=3 ngoai [5,10] phai canh bao"
    print(f"  new_level=3 -> out_of_range={result.out_of_range} OK")

    result2 = fc.compute(hr_actual, HR_TARGET_CENTER, hr_prev, DT, current_level=7)
    assert result2.out_of_range is False, "level=7 trong [5,10] khong duoc canh bao"
    print(f"  new_level=7 -> out_of_range={result2.out_of_range} OK\n")


def main():
    test_15_rule_cells()
    test_deadband()
    test_clamp_bien()
    test_out_of_range_warning()
    print("OK - FuzzyController hoat dong dung thiet ke (15 luat + deadband + clamp + warning)")


if __name__ == "__main__":
    main()
