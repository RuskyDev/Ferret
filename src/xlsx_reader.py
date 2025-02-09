from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
import sys
import csv
import pandas as pd

class CSVReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Reader")
        self.setGeometry(100, 100, 800, 300)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        self.load_file("./cielowigle.com.xlsx")

    def load_file(self, file_path):
        if file_path.endswith(".csv"):
            self.load_csv(file_path)
        elif file_path.endswith(".xlsx"):
            self.load_xlsx(file_path)

    def load_csv(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            data = list(reader)
        self.populate_table(data)

    def load_xlsx(self, file_path):
        df = pd.read_excel(file_path, dtype=str)
        data = [df.columns.tolist()] + df.values.tolist()
        self.populate_table(data)

    def populate_table(self, data):
        if data:
            self.table.setRowCount(len(data))
            self.table.setColumnCount(len(data[0]))

            for row_idx, row in enumerate(data):
                for col_idx, item in enumerate(row):
                    self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))

            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()

app = QApplication(sys.argv)
window = CSVReader()
window.show()
sys.exit(app.exec_())
