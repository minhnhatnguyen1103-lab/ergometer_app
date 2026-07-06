"""
control/fuzzy_controller.py
-------------------------------
M1 theo docsclaude/IMPLEMENTATION_PLAN.md muc 3.1: bo suy luan mo (Mamdani)
quyet dinh can doi Delta_level bao nhieu de keo HR ve vung muc tieu. CHI dung
trong pha Main (Warmup dung level co dinh, Cooldown dung ramp tuyen tinh -
xem control/session_manager.py).

Tu viet (khong dung scikit-fuzzy/simpful) - ly do: an toan dong goi .exe
(khong keo them dependency nang nhu networkx), moi cong thuc nam trong 1 ham
de kiem tra tung luat mot voi hoi dong, va bai toan qua nho (15 luat) de mot
framework tong quat co loi ich that. Xem GIAI_THICH_DE_HIEU.md muc 4 de biet
ly do day du.

Hai dau vao (cau truc PD mo):
  e  = HR_target_center - HR_actual   (bpm)   -> HR thap hon muc tieu => e>0 => tang level
  de = (HR_now - HR_prev) / dt        (bpm/s) -> HR dang tang/giam    -> don dau, tranh overshoot

Dau ra: delta_level trong {-2,-1,0,+1,+2}, cong voi current_level roi hard
clamp ve [LEVEL_MIN, LEVEL_MAX].
"""

from dataclasses import dataclass

import numpy as np

from core import config


def _trapmf(x: np.ndarray, a: float, b: float, c: float, d: float) -> np.ndarray:
    """Hinh thang: 0 truoc a, len tuyen tinh a->b, dinh (=1) tu b->c,
    xuong tuyen tinh c->d, 0 sau d. Dung lam "vai" (shoulder) bao hoa o
    2 dau vu tru (NB, PB, FALL, RISE) - gia tri khong giam/tang vo han
    ma giu nguyen muc do thanh vien = 1."""
    y = np.zeros_like(x, dtype=np.float64)
    if b > a:
        m = (x >= a) & (x < b)
        y[m] = (x[m] - a) / (b - a)
    y[(x >= b) & (x <= c)] = 1.0
    if d > c:
        m = (x > c) & (x <= d)
        y[m] = (d - x[m]) / (d - c)
    return y


def _trimf(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """Tam giac: 0 tai a, dinh (=1) tai b, ve 0 tai c."""
    return _trapmf(x, a, b, b, c)


@dataclass
class FuzzyResult:
    delta_level: int      # {-2..+2} - da qua deadband + lam tron
    new_level: int         # current_level + delta_level, da hard clamp [LEVEL_MIN, LEVEL_MAX]
    error: float           # e = hr_target_center - hr_actual
    error_rate: float      # de = (hr_actual - hr_prev) / dt
    crisp_output: float    # gia tri centroid THO truoc deadband/lam tron (de doi chieu/bao cao)
    out_of_range: bool     # new_level ngoai [LEVEL_EXPECTED_MIN, LEVEL_EXPECTED_MAX]? (chi canh bao)


class FuzzyController:
    """Bo dieu khien mo Mamdani, hop thanh min, hop luat max, giai mo centroid.

    Vu tru rieng cho tung bien (khong doi qua config.py vi day la tham so
    tune thuat toan noi bo, giong cach signals/pan_tompkins.py giu WIN_MWI,
    REF... la class constant thay vi core/config.py).
    """

    # --- Vu tru `e` (bpm) va cac tap mo: NB, NS, ZE, PS, PB ---
    E_UNIVERSE = np.linspace(-30.0, 30.0, 601)
    # ZE dinh 0, chan +-6 (dung bang deadband HR_DEADBAND_BPM=3 lam mot nua)
    E_SETS = {
        "NB": ("trap", -30.0, -30.0, -18.0, -8.0),
        "NS": ("tri", -18.0, -8.0, 0.0),
        "ZE": ("tri", -6.0, 0.0, 6.0),
        "PS": ("tri", 0.0, 8.0, 18.0),
        "PB": ("trap", 8.0, 18.0, 30.0, 30.0),
    }

    # --- Vu tru `de` (bpm/cua so) va cac tap mo: FALL, STEADY, RISE ---
    DE_UNIVERSE = np.linspace(-10.0, 10.0, 401)
    DE_SETS = {
        "FALL": ("trap", -10.0, -10.0, -4.0, 0.0),
        "STEADY": ("tri", -4.0, 0.0, 4.0),
        "RISE": ("trap", 0.0, 4.0, 10.0, 10.0),
    }

    # --- Vu tru dau ra `delta_level` va cac tap mo (singleton labels NB..PB = -2..+2) ---
    OUT_UNIVERSE = np.linspace(-2.5, 2.5, 501)
    OUT_SETS = {
        "NB": ("trap", -2.5, -2.5, -2.0, -1.0),
        "NS": ("tri", -2.0, -1.0, 0.0),
        "ZE": ("tri", -1.0, 0.0, 1.0),
        "PS": ("tri", 0.0, 1.0, 2.0),
        "PB": ("trap", 1.0, 2.0, 2.5, 2.5),
    }
    OUT_LABEL_TO_INT = {"NB": -2, "NS": -1, "ZE": 0, "PS": 1, "PB": 2}

    # --- Bang 15 luat (hang = nhan e, cot = nhan de) - dung nguyen ban IMPLEMENTATION_PLAN.md 3.1 ---
    RULE_TABLE = {
        ("NB", "RISE"): "NB", ("NB", "STEADY"): "NB", ("NB", "FALL"): "NS",
        ("NS", "RISE"): "NS", ("NS", "STEADY"): "NS", ("NS", "FALL"): "ZE",
        ("ZE", "RISE"): "NS", ("ZE", "STEADY"): "ZE", ("ZE", "FALL"): "PS",
        ("PS", "RISE"): "ZE", ("PS", "STEADY"): "PS", ("PS", "FALL"): "PS",
        ("PB", "RISE"): "PS", ("PB", "STEADY"): "PB", ("PB", "FALL"): "PB",
    }

    # Nguong "|de| nho" de ket hop voi vung chet cung |e|<=HR_DEADBAND_BPM.
    # Dac ta khong cho so cu the cho "de nho" - chon bang mot nua be rong
    # tap STEADY (dinh 0, chan +-4) de nhat quan voi thiet ke tap mo o tren.
    DEADBAND_DE_THRESHOLD = 2.0

    def __init__(self, cfg=config):
        self.config = cfg

    def _memberships(self, value: float, universe: np.ndarray, sets: dict) -> dict:
        x = np.array([value])
        out = {}
        for label, spec in sets.items():
            kind = spec[0]
            if kind == "trap":
                _, a, b, c, d = spec
                out[label] = float(_trapmf(x, a, b, c, d)[0])
            else:
                _, a, b, c = spec
                out[label] = float(_trimf(x, a, b, c)[0])
        return out

    def _defuzzify_centroid(self, rule_strengths: dict) -> float:
        """Hop thanh MIN (AND cua 2 dau vao), hop luat MAX (aggregate tren
        cung nhan dau ra), giai mo CENTROID tren vu tru lien tuc."""
        agg = np.zeros_like(self.OUT_UNIVERSE)
        for out_label, strength in rule_strengths.items():
            if strength <= 0.0:
                continue
            spec = self.OUT_SETS[out_label]
            if spec[0] == "trap":
                _, a, b, c, d = spec
                mf = _trapmf(self.OUT_UNIVERSE, a, b, c, d)
            else:
                _, a, b, c = spec
                mf = _trimf(self.OUT_UNIVERSE, a, b, c)
            clipped = np.minimum(mf, strength)
            agg = np.maximum(agg, clipped)

        total = agg.sum()
        if total <= 0.0:
            return 0.0
        return float((agg * self.OUT_UNIVERSE).sum() / total)

    def compute(self, hr_actual: float, hr_target_center: float,
                hr_prev: float, dt: float, current_level: int) -> FuzzyResult:
        """Tinh mot lan cap nhat Fuzzy. Goi moi FUZZY_UPDATE_INTERVAL_SEC (5-8s)
        trong pha Main, VOI current_level da doc tu telemetry (khong dung gia
        tri cache) - xem session_manager.py de biet ly do bat buoc."""
        e = hr_target_center - hr_actual
        de = (hr_actual - hr_prev) / dt if dt > 0 else 0.0

        e_mu = self._memberships(e, self.E_UNIVERSE, self.E_SETS)
        de_mu = self._memberships(de, self.DE_UNIVERSE, self.DE_SETS)

        # Hop rule strength theo nhan dau ra (nhieu luat co the cung tro ve 1 nhan)
        rule_strengths: dict[str, float] = {}
        for (e_label, de_label), out_label in self.RULE_TABLE.items():
            strength = min(e_mu.get(e_label, 0.0), de_mu.get(de_label, 0.0))
            if strength <= 0.0:
                continue
            rule_strengths[out_label] = max(rule_strengths.get(out_label, 0.0), strength)

        crisp = self._defuzzify_centroid(rule_strengths)

        # Chot chan 1: vung chet cung - |e| nho VA |de| nho => ep delta=0
        if abs(e) <= self.config.HR_DEADBAND_BPM and abs(de) <= self.DEADBAND_DE_THRESHOLD:
            delta_level = 0
        else:
            delta_level = int(np.clip(round(crisp), -2, 2))

        new_level = int(np.clip(current_level + delta_level, self.config.LEVEL_MIN, self.config.LEVEL_MAX))
        out_of_range = not (self.config.LEVEL_EXPECTED_MIN <= new_level <= self.config.LEVEL_EXPECTED_MAX)

        return FuzzyResult(
            delta_level=delta_level,
            new_level=new_level,
            error=e,
            error_rate=de,
            crisp_output=crisp,
            out_of_range=out_of_range,
        )
