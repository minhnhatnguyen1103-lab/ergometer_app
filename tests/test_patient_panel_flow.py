"""
tests/test_patient_panel_flow.py
------------------------------------
Test tu dong: chon "Heart Rate Control" -> nhap thong tin co ban ->
nhap IPAQ -> xac nhan PatientProfile tao dung, phan loai dung.

Chay: python tests/test_patient_panel_flow.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow
from data.patient import Sex


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    steps_done = []
    received_patient = {}

    def step1_select_hrc_mode():
        print("[1] Chon mode Heart Rate Control...")
        window.mode_select_view.mode_selected.emit("heart_rate_control")
        assert window.stack.currentWidget() is window.patient_panel
        steps_done.append("select_mode")

    def step2_fill_basic_info():
        print("[2] Dien thong tin co ban...")
        panel = window.patient_panel
        panel.basic_page.name_input.setText("Nguyen Van Test")
        panel.basic_page.age_input.setValue(25)
        panel.basic_page.sex_input.setCurrentIndex(0)  # Nam
        panel.basic_page.height_input.setValue(175)
        panel.basic_page.weight_input.setValue(70)
        panel.basic_page._on_next()
        assert panel.stack.currentWidget() is panel.ipaq_page
        steps_done.append("basic_info")

    def step3_fill_ipaq_active():
        print("[3] Dien IPAQ (truong hop Active: 4 ngay x 40 phut vigorous)...")
        panel = window.patient_panel
        panel.ipaq_page.vig_days.setValue(4)
        panel.ipaq_page.vig_min.setValue(40)
        panel.ipaq_page.mod_days.setValue(0)
        panel.ipaq_page.mod_min.setValue(0)
        panel.ipaq_page._on_submit()
        assert panel.stack.currentWidget() is panel.result_page
        patient = panel._current_patient
        print(f"    HRmax={patient.hr_max}, MVPA={patient.mvpa_min_per_week}, nhom={patient.ipaq_activity_level.value}")
        assert patient.ipaq_activity_level.value == "active", "4x40=160 phut vigorous >=75 phai la Active"
        received_patient['obj'] = patient
        steps_done.append("ipaq_submit")

    def step4_check_no_hrmax_label():
        print("[4] Kiem tra UI khong hien HRmax (SHOW_DEBUG_INFO=False)...")
        panel = window.patient_panel
        debug_text = panel.basic_page.debug_label.text()
        assert debug_text == "", f"debug_label phai rong khi SHOW_DEBUG_INFO=False, nhung dang la: '{debug_text}'"
        steps_done.append("no_hrmax_shown")

    def _close_any_modal():
        w = app.activeModalWidget()
        if w:
            w.accept()

    def step5_continue_to_next():
        print("[5] Bam Tiep tuc, kiem tra signal patient_ready phat dung...")
        panel = window.patient_panel
        panel.patient_ready.connect(lambda p: steps_done.append("patient_ready_emitted"))
        # QMessageBox trong MainWindow se block (modal) - hen gio dong no lai
        # trong luc no chay nested event loop
        QTimer.singleShot(150, _close_any_modal)
        panel._on_continue()

    def finish():
        expected = ["select_mode", "basic_info", "ipaq_submit", "no_hrmax_shown", "patient_ready_emitted"]
        print(f"\nCac buoc da hoan thanh: {steps_done}")
        assert steps_done == expected, f"Thieu buoc! Ky vong {expected}"
        print("\nOK - toan bo luong PatientPanel hoat dong dung")
        app.quit()

    QTimer.singleShot(200, step1_select_hrc_mode)
    QTimer.singleShot(400, step2_fill_basic_info)
    QTimer.singleShot(600, step3_fill_ipaq_active)
    QTimer.singleShot(800, step4_check_no_hrmax_label)
    QTimer.singleShot(1000, step5_continue_to_next)
    QTimer.singleShot(1500, finish)

    app.exec()


if __name__ == "__main__":
    main()
