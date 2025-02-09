import sys
import os
import re
import time
import json
import subprocess
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtGui import QFontDatabase, QFont

VERSION = 1

class RScraper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"RScraper v{VERSION}")
        self.setGeometry(100, 100, 800, 300)
        self.setFixedSize(800, 300)
        self.scrape_process = None
        self.json_filename = None

        font_id = QFontDatabase.addApplicationFont("./fonts/Roboto-Regular.ttf")
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                self.font = QFont(font_families[0], 12)
        else:
            self.font = QFont("Arial", 12)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
                color: white;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #444;
                padding: 5px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton {
                border-radius: 5px;
                font-size: 14px;
                padding: 5px;
                font-weight: 500;
            }
            QPushButton#scrapeButton {
                background-color: #0078D7;
                color: white;
            }
            QPushButton#scrapeButton:hover {
                background-color: #005a9e;
            }
        """)

        self.label = QLabel("Enter the Website URL to Scrape:", self)
        self.label.setGeometry(10, 10, 300, 25)
        self.label.setFont(self.font)

        self.url_input = QLineEdit(self)
        self.url_input.setGeometry(10, 40, 780, 30)
        self.url_input.setFont(self.font)

        self.scrape_button = QPushButton("Scrape", self)
        self.scrape_button.setGeometry(10, 80, 780, 30)
        self.scrape_button.setFont(self.font)
        self.scrape_button.setObjectName("scrapeButton")
        self.scrape_button.clicked.connect(self.start_scrape)

        self.stats_label = QLabel("", self)
        self.stats_label.setGeometry(10, 130, 780, 100)
        self.stats_label.setFont(self.font)
        self.update_stats()

    def closeEvent(self, event):
        if self.scrape_process:
            self.scrape_process.terminate()
        event.accept()

    def is_valid_url(self, url):
        return re.match(r"^(https?://)?([a-zA-Z0-9.-]+)\.[a-zA-Z]{2,}(/.*)?$", url) is not None

    def start_scrape(self):
        url = self.url_input.text().strip()
        if not self.is_valid_url(url):
            QMessageBox.critical(self, "Invalid URL", "Please enter a valid website URL.")
            return

        self.set_button_state("Starting...", "background-color: orange; color: white;", disabled=True)

        domain = re.sub(r"https?://", "", url).split('/')[0]
        self.json_filename = f"{domain}.json"

        thread = threading.Thread(target=self.run_scraper, args=(url,))
        thread.start()

    def run_scraper(self, url):
        self.scrape_process = subprocess.Popen(["py", "./scraper.py", "--website-url", url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        monitor_thread = threading.Thread(target=self.monitor_scraper)
        monitor_thread.start()

    def monitor_scraper(self):
        while self.scrape_process.poll() is None:
            if os.path.exists(self.json_filename):
                self.update_stats_from_file()
            time.sleep(1)

        self.reset_scrape_button()

    def update_stats_from_file(self):
        try:
            with open(self.json_filename, "r", encoding="utf-8") as file:
                data = json.load(file)

            stats = data.get("stats", {})
            total_pages = stats.get("TOTAL_PAGES_SCRAPED", 0)
            extracted_emails = stats.get("EXTRACTED_EMAILS", 0)
            extracted_phone_numbers = stats.get("EXTRACTED_PHONE_NUMBERS", 0)
            total_social_links = stats.get("TOTAL_SOCIAL_MEDIA_LINKS", 0)

            self.stats_label.setText(
                f"Total Pages Scraped: {total_pages}\n"
                f"Extracted Emails: {extracted_emails}\n"
                f"Extracted Phone Numbers: {extracted_phone_numbers}\n"
                f"Extracted Social Media Links: {total_social_links}"
            )

            self.set_button_state("Stop", "background-color: red; color: white;", disabled=False)
            self.scrape_button.clicked.disconnect()
            self.scrape_button.clicked.connect(self.stop_scraper)

        except Exception as e:
            print(f"Error reading JSON: {e}")

    def stop_scraper(self):
        if self.scrape_process:
            self.scrape_process.terminate()
            self.scrape_process = None
        self.reset_scrape_button()

    def reset_scrape_button(self):
        self.set_button_state("Scrape", "background-color: #0078D7; color: white;", disabled=False)
        self.scrape_button.clicked.disconnect()
        self.scrape_button.clicked.connect(self.start_scrape)

    def set_button_state(self, text, style, disabled):
        self.scrape_button.setText(text)
        self.scrape_button.setStyleSheet(style)
        self.scrape_button.setDisabled(disabled)

    def update_stats(self):
        self.stats_label.setText(
            "Total Pages Scraped: 0\n"
            "Extracted Emails: 0\n"
            "Extracted Phone Numbers: 0\n"
            "Extracted Social Media Links: 0"
        )

app = QApplication(sys.argv)
window = RScraper()
window.show()
sys.exit(app.exec_())
