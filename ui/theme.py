"""Clinical-dark design system shared by every PyQt6 view."""

BG = "#0B0F14"
SURFACE = "#121923"
ELEVATED = "#18212D"
BORDER = "#263445"
TEXT = "#EAF2F8"
MUTED = "#8EA0B5"
BRAND = "#20C7D9"
SUCCESS = "#3DDC97"
WARNING = "#FFB44A"
DANGER = "#FF5D68"
INFO = "#4AA3FF"
PURPLE = "#A78BFA"


def application_stylesheet() -> str:
    return f"""
        * {{
            font-family: "Segoe UI", "Inter", sans-serif;
            font-size: 14px;
            color: {TEXT};
        }}
        QMainWindow, QStackedWidget, QWidget {{ background: {BG}; }}
        QLabel {{ background: transparent; }}
        QToolTip {{
            background: {ELEVATED}; color: {TEXT}; border: 1px solid {BORDER};
            padding: 6px 8px;
        }}

        QFrame#pageHeader {{ background: transparent; }}
        QLabel#eyebrow {{
            color: {BRAND}; font-size: 11px; font-weight: 700;
            letter-spacing: 1px; max-height: 22px;
        }}
        QLabel#pageTitle {{ color: {TEXT}; font-size: 28px; font-weight: 700; }}
        QLabel#pageSubtitle {{ color: {MUTED}; font-size: 14px; }}
        QLabel#sectionTitle {{
            color: {TEXT}; font-size: 17px; font-weight: 700; max-height: 32px;
        }}
        QLabel#mutedText, QLabel#metricUnit {{ color: {MUTED}; font-size: 12px; }}
        QLabel#monoText {{
            color: {MUTED}; font-family: "Cascadia Mono", "Consolas", monospace;
        }}
        QLabel#metricValue {{
            color: {TEXT}; font-family: "Cascadia Mono", "Consolas", monospace;
            font-size: 34px; font-weight: 700;
        }}
        QLabel#metricValue[compact="true"] {{ font-size: 20px; }}
        QLabel#hrValue {{
            color: {TEXT}; font-family: "Cascadia Mono", "Consolas", monospace;
            font-size: 72px; font-weight: 700;
        }}
        QLabel#clock {{
            color: {TEXT}; font-family: "Cascadia Mono", "Consolas", monospace;
            font-size: 16px; font-weight: 600;
        }}

        QFrame#card, QFrame#metricCard, QFrame#plotCard, QFrame#summaryHero {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
        }}
        QFrame#metricCard {{ background: {ELEVATED}; border-radius: 10px; }}
        QFrame#plotCard {{ border-color: #304257; }}
        QFrame#hrHero {{
            background: {SURFACE}; border: 2px solid {BORDER}; border-radius: 16px;
        }}
        QFrame#hrHero[zoneState="in"] {{ border-color: {SUCCESS}; }}
        QFrame#hrHero[zoneState="out"] {{ border-color: {DANGER}; }}

        QFrame#shellRail {{
            background: #0F1620; border-right: 1px solid {BORDER};
        }}
        QLabel#railBrand {{ color: {TEXT}; font-size: 15px; font-weight: 800; }}
        QLabel#railStep {{
            color: #64758A; border-left: 2px solid transparent;
            padding: 10px 12px; font-size: 12px;
        }}
        QLabel#railStep[state="current"] {{
            color: {TEXT}; background: #142A34; border-left-color: {BRAND};
            font-weight: 700;
        }}
        QLabel#railStep[state="done"] {{ color: {SUCCESS}; }}

        QLabel#statusBadge, QLabel#phaseChip {{
            border-radius: 10px; padding: 5px 10px; font-size: 11px; font-weight: 800;
        }}
        QLabel#statusBadge[status="neutral"] {{ background: #243142; color: #B9C7D8; }}
        QLabel#statusBadge[status="live"] {{ background: #12382F; color: {SUCCESS}; }}
        QLabel#statusBadge[status="demo"] {{ background: #3A2B13; color: {WARNING}; }}
        QLabel#statusBadge[status="warning"] {{ background: #3A2B13; color: {WARNING}; }}
        QLabel#statusBadge[status="error"] {{ background: #411C25; color: {DANGER}; }}
        QLabel#phaseChip[phase="WARMUP"] {{ background: #132E4A; color: {INFO}; }}
        QLabel#phaseChip[phase="MAIN"] {{ background: #12383B; color: {BRAND}; }}
        QLabel#phaseChip[phase="COOLDOWN"] {{ background: #2C2345; color: {PURPLE}; }}
        QLabel#phaseChip[phase="DONE"] {{ background: #12382F; color: {SUCCESS}; }}

        QLabel#alertBanner {{
            background: #3A2B13; border: 1px solid #76521E; border-radius: 9px;
            color: {WARNING}; font-weight: 700; padding: 10px 12px;
        }}
        QLabel#alertBanner[severity="danger"] {{
            background: #411C25; border-color: #7B2D3A; color: {DANGER};
        }}
        QLabel#successBanner {{
            background: #12382F; border: 1px solid #246B57; border-radius: 9px;
            color: {SUCCESS}; font-weight: 700; padding: 10px 12px;
        }}

        QLineEdit {{
            background: #0F1620; border: 1px solid #34465B; border-radius: 8px;
            min-height: 38px; padding: 2px 10px; selection-background-color: {BRAND};
        }}
        QLineEdit:focus {{ border: 2px solid {BRAND}; }}
        QSpinBox, QComboBox {{ background: #0F1620; color: {TEXT}; min-height: 38px; }}
        QComboBox QAbstractItemView {{
            background: {ELEVATED}; color: {TEXT}; selection-background-color: #214554;
        }}

        QCheckBox {{ spacing: 10px; }}
        QCheckBox#toggleCard {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
            padding: 14px 16px; min-height: 28px;
        }}
        QCheckBox#toggleCard:checked {{ background: #102E31; border-color: {BRAND}; }}
        QCheckBox::indicator {{
            width: 19px; height: 19px; border: 1px solid #60758C;
            border-radius: 5px; background: #0F1620;
        }}
        QCheckBox::indicator:checked {{ background: {BRAND}; border-color: {BRAND}; }}

        QPushButton {{
            background: {ELEVATED}; border: 1px solid #34465B; border-radius: 9px;
            color: {TEXT}; font-weight: 700; min-height: 40px; padding: 5px 15px;
        }}
        QPushButton:hover {{ background: #223043; border-color: #526A83; }}
        QPushButton:pressed {{ background: #0F1620; }}
        QPushButton:focus {{ border: 2px solid {BRAND}; }}
        QPushButton:disabled {{ background: #111821; border-color: #202B38; color: #526174; }}
        QPushButton[variant="primary"] {{ background: {BRAND}; border-color: {BRAND}; color: #071014; }}
        QPushButton[variant="primary"]:hover {{ background: #50D8E6; border-color: #50D8E6; }}
        QPushButton[variant="danger"] {{ background: #C93645; border-color: {DANGER}; color: #FFFFFF; }}
        QPushButton[variant="danger"]:hover {{ background: #E54857; }}
        QPushButton[variant="ghost"] {{ background: transparent; border-color: transparent; color: {MUTED}; }}
        QPushButton[variant="ghost"]:hover {{ background: #121C28; border-color: {BORDER}; }}
        QPushButton#featureCard {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px;
            color: {TEXT}; font-size: 17px; font-weight: 700; text-align: left;
            padding: 24px; min-height: 150px;
        }}
        QPushButton#featureCard:hover {{ background: #162330; border-color: {BRAND}; }}

        QListWidget {{
            background: #0F1620; border: 1px solid {BORDER}; border-radius: 9px;
            font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px;
            padding: 5px;
        }}
        QListWidget::item {{ padding: 5px 7px; border-bottom: 1px solid #1D2937; }}
        QListWidget::item:selected {{ background: #193442; }}

        QProgressBar {{
            background: #0F1620; border: 1px solid {BORDER}; border-radius: 5px;
            min-height: 9px; max-height: 9px; text-align: center; color: transparent;
        }}
        QProgressBar::chunk {{ background: {BRAND}; border-radius: 4px; }}
        QScrollArea {{ border: none; background: transparent; }}
        QScrollArea > QWidget > QWidget {{ background: transparent; }}
        QMessageBox {{ background: {SURFACE}; }}
    """
