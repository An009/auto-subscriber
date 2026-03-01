import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLineEdit, QLabel, 
                               QFileDialog, QTableWidget, QTableWidgetItem, 
                               QProgressBar, QTextEdit, QCheckBox, QSpinBox,
                               QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, Signal, Slot, QObject
from PySide6.QtGui import QColor, QBrush

from .subscriber import SubscriberWorker
from .database import Database
from .utils import parse_emails_file

class WorkerSignals(QObject):
    progress = Signal(int, int, str, str)
    log = Signal(str)
    result = Signal(str, str, int, str)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Newsletter Subscriber")
        self.resize(1000, 700)
        self.worker = None
        self.urls = []
        self.emails_list = []
        self.signals = WorkerSignals()
        
        self.signals.progress.connect(self.update_progress)
        self.signals.log.connect(self.append_log)
        self.signals.result.connect(self.update_table)
        
        self.init_ui()
        self.load_history()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Top Controls - URLs
        urls_layout = QHBoxLayout()
        self.btn_load = QPushButton("Load URLs File")
        self.btn_load.clicked.connect(self.load_urls)
        urls_layout.addWidget(self.btn_load)
        
        self.lbl_urls = QLabel("No URLs loaded")
        urls_layout.addWidget(self.lbl_urls)
        urls_layout.addStretch()
        layout.addLayout(urls_layout)

        # Top Controls - Emails
        emails_layout = QHBoxLayout()
        self.btn_load_emails = QPushButton("Upload Emails File")
        self.btn_load_emails.clicked.connect(self.load_emails)
        emails_layout.addWidget(self.btn_load_emails)
        
        self.lbl_emails = QLabel("No emails loaded")
        emails_layout.addWidget(self.lbl_emails)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Or enter a single email here...")
        emails_layout.addWidget(self.txt_email)
        
        layout.addLayout(emails_layout)
        
        # Config
        config_layout = QHBoxLayout()
        self.chk_headless = QCheckBox("Headless Mode (Hide Browser)")
        self.chk_headless.setChecked(False)
        config_layout.addWidget(self.chk_headless)
        
        config_layout.addWidget(QLabel("Retries:"))
        self.spin_retries = QSpinBox()
        self.spin_retries.setValue(3)
        self.spin_retries.setMinimum(1)
        config_layout.addWidget(self.spin_retries)

        config_layout.addWidget(QLabel("Page Ready Wait (ms):"))
        self.spin_wait = QSpinBox()
        self.spin_wait.setRange(0, 20000)
        self.spin_wait.setSingleStep(1000)
        self.spin_wait.setValue(3000)
        config_layout.addWidget(self.spin_wait)
        
        config_layout.addStretch()
        layout.addLayout(config_layout)
        
        # Action Buttons
        actions_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.start_processing)
        actions_layout.addWidget(self.btn_start)
        
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self.pause_processing)
        self.btn_pause.setEnabled(False)
        actions_layout.addWidget(self.btn_pause)

        self.btn_resume = QPushButton("Resume")
        self.btn_resume.clicked.connect(self.resume_processing)
        self.btn_resume.setEnabled(False)
        actions_layout.addWidget(self.btn_resume)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_processing)
        self.btn_cancel.setEnabled(False)
        actions_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(actions_layout)
        
        # Status / Progress
        self.lbl_status = QLabel("Ready")
        layout.addWidget(self.lbl_status)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Stats
        self.lbl_stats = QLabel("Succeeded: 0 | Failed: 0 | Remaining: 0")
        layout.addWidget(self.lbl_stats)
        
        # Log & Table Split
        split_layout = QHBoxLayout()
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        split_layout.addWidget(self.log_area, 1)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["URL", "Status", "Attempts", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.cellClicked.connect(self.on_table_click)
        split_layout.addWidget(self.table, 2)
        
        layout.addLayout(split_layout)

    def load_urls(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open URLs File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    self.urls = [line.strip() for line in f if line.strip()]
                self.lbl_urls.setText(f"{len(self.urls)} URLs loaded")
                self.update_stats()
            except Exception as e:
                self.append_log(f"Failed to read URLs file: {e}")

    def load_emails(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Emails File", "", "Text/CSV Files (*.txt *.csv);;All Files (*)")
        if file_name:
            try:
                valid, invalid = parse_emails_file(file_name)
                
                if invalid:
                    msg = f"Found {len(invalid)} invalid email(s).\n\nExamples:\n" + "\n".join(invalid[:5])
                    msg += "\n\nDo you want to continue with only the valid emails?"
                    reply = QMessageBox.question(self, "Invalid Emails Detected", msg, QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.No:
                        return
                        
                self.emails_list = valid
                self.lbl_emails.setText(f"{len(valid)} emails loaded")
                self.append_log(f"Loaded {len(valid)} valid emails (deduplicated).")
            except Exception as e:
                self.append_log(f"Failed to read emails file: {e}")
                QMessageBox.critical(self, "Error", str(e))

    def load_history(self):
        db = Database()
        jobs = db.get_all_jobs()
        self.table.setRowCount(0)
        for job in jobs:
            self.add_table_row(job['url'], job['status'], job['attempts'], job['error'])

    def add_table_row(self, url, status, attempts, message):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(url))
        
        item_status = QTableWidgetItem(status)
        if status == "SUCCESS":
            item_status.setBackground(QBrush(QColor(100, 255, 100, 100)))
        elif status in ["ERROR", "FAILED_TO_SUBMIT", "FAILED_TO_FILL_EMAIL", "NO_FORM_FOUND", "TIMEOUT"]:
            item_status.setBackground(QBrush(QColor(255, 100, 100, 100)))
            
        self.table.setItem(row, 1, item_status)
        self.table.setItem(row, 2, QTableWidgetItem(str(attempts)))
        self.table.setItem(row, 3, QTableWidgetItem(str(message)))
        
        self.update_stats()

    def update_stats(self):
        succeeded = 0
        failed = 0
        for r in range(self.table.rowCount()):
            s = self.table.item(r, 1).text()
            if s == "SUCCESS":
                succeeded += 1
            elif s in ["ERROR", "FAILED_TO_SUBMIT", "FAILED_TO_FILL_EMAIL", "NO_FORM_FOUND", "TIMEOUT"]:
                failed += 1
                
        # Approximate remaining logic based on jobs
        remaining = max(0, (len(self.urls) * max(1, len(self.emails_list))) - (succeeded + failed))
        self.lbl_stats.setText(f"Succeeded: {succeeded} | Failed: {failed} | Remaining: {remaining}")

    def on_table_click(self, row, column):
        url = self.table.item(row, 0).text()
        import webbrowser
        webbrowser.open(url)

    @Slot(int, int, str, str)
    def update_progress(self, current, total, url, step):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        self.lbl_status.setText(f"Step: {step} | Target: {url}")
        
        if current >= total and total > 0:
            self.btn_start.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(False)

    @Slot(str)
    def append_log(self, text):
        self.log_area.append(text)

    @Slot(str, str, int, str)
    def update_table(self, url, status, attempts, message):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == url:
                self.table.setItem(row, 1, QTableWidgetItem(status))
                self.table.setItem(row, 2, QTableWidgetItem(str(attempts)))
                self.table.setItem(row, 3, QTableWidgetItem(str(message)))
                
                item_status = self.table.item(row, 1)
                if status == "SUCCESS":
                    item_status.setBackground(QBrush(QColor(100, 255, 100, 100)))
                elif status in ["ERROR", "FAILED_TO_SUBMIT", "FAILED_TO_FILL_EMAIL", "NO_FORM_FOUND", "TIMEOUT"]:
                    item_status.setBackground(QBrush(QColor(255, 100, 100, 100)))
                    
                self.update_stats()
                return
                
        self.add_table_row(url, status, attempts, message)

    def start_processing(self):
        if not self.urls:
            self.append_log("No URLs loaded.")
            return
            
        emails_to_process = self.emails_list.copy()
        single_email = self.txt_email.text().strip()
        if single_email and single_email not in emails_to_process:
            emails_to_process.append(single_email)
            
        if not emails_to_process:
            self.append_log("Please enter an email or upload an emails file.")
            return
            
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)
        self.log_area.clear()
        
        self.worker = SubscriberWorker(
            urls=self.urls,
            emails=emails_to_process,
            headless=self.chk_headless.isChecked(),
            retries=self.spin_retries.value(),
            extra_wait=self.spin_wait.value(),
            progress_callback=self.signals.progress.emit,
            log_callback=self.signals.log.emit,
            result_callback=self.signals.result.emit
        )
        self.worker.start()

    def pause_processing(self):
        if self.worker:
            self.worker.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)
            self.append_log("Pausing...")

    def resume_processing(self):
        if self.worker:
            self.worker.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)
            self.append_log("Resuming...")

    def cancel_processing(self):
        if self.worker:
            self.worker.stop()
            self.btn_cancel.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(False)
            self.append_log("Cancelling... Please wait for the current task to finish.")

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
            self.worker.join(timeout=2.0)
        event.accept()

def run_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
