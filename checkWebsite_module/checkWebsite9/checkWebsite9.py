# main.py
import sys
import threading
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QHBoxLayout,
    QMessageBox,
)
from PyQt6.QtCore import QTimer

from monitor9 import Monitor


class WebsiteMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网站可用性监控 - 钉钉推送9")
        self.setFixedSize(580, 280)
        self.monitoring = False
        self.stop_event = threading.Event()
        self.thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        h_layout_url = QHBoxLayout()
        h_layout_url.addWidget(QLabel("监控网站 URL："))
        self.url_input = QLineEdit("https://www.wic-power.com")
        h_layout_url.addWidget(self.url_input)
        layout.addLayout(h_layout_url)

        h_layout_interval_err = QHBoxLayout()
        h_layout_interval_err.addWidget(QLabel("异常检测间隔（秒）："))
        self.interval_input_err = QLineEdit("180")
        h_layout_interval_err.addWidget(self.interval_input_err)
        layout.addLayout(h_layout_interval_err)

        h_layout_interval_ok = QHBoxLayout()
        h_layout_interval_ok.addWidget(QLabel("正常检测间隔（秒）："))
        self.interval_input_ok = QLineEdit("600")
        h_layout_interval_ok.addWidget(self.interval_input_ok)
        layout.addLayout(h_layout_interval_ok)

        h_layout_token = QHBoxLayout()
        h_layout_token.addWidget(QLabel("钉钉 access_token："))
        self.token_input = QLineEdit(
            "2790e24fa6bb40ba86208e99c4b02223941b51a5b61d0f0e08820d3f461e330d"
            #  "aa0366d18f2307daa196c4f96546ed629a92b110448ed104614fe9566dfa1b14"
        )
        h_layout_token.addWidget(self.token_input)
        layout.addLayout(h_layout_token)

        self.check_immediate = QCheckBox("启动后立即检测一次")
        layout.addWidget(self.check_immediate)

        self.status_label = QLabel("状态：未开始监控")
        layout.addWidget(self.status_label)

        self.start_btn = QPushButton("开始监控")
        self.start_btn.clicked.connect(self.toggle_monitoring)
        layout.addWidget(self.start_btn)

        self.setLayout(layout)

    def toggle_monitoring(self):
        if self.monitoring:
            self.monitoring = False
            self.stop_event.set()
            self.start_btn.setText("开始监控")
            self.update_status("已停止监控")
        else:
            url = self.url_input.text().strip()
            token = self.token_input.text().strip()
            try:
                interval_err = int(self.interval_input_err.text().strip())
                interval_ok = int(self.interval_input_ok.text().strip())
                if interval_err < 10 or interval_ok < 10:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(
                    self, "输入错误", "请输入有效的时间间隔（整数且>=10）"
                )
                return

            if not url or not token:
                QMessageBox.warning(self, "输入错误", "请填写完整的URL和token")
                return

            self.monitoring = True
            self.stop_event.clear()
            self.start_btn.setText("停止监控")
            self.update_status(f"开始监控：{url}")

            immediate = self.check_immediate.isChecked()
            monitor = Monitor(
                url=url,
                token=token,
                interval_ok=interval_ok,
                interval_err=interval_err,
                callback_status=self.update_status,
                stop_event=self.stop_event,
            )
            self.thread = threading.Thread(
                target=monitor.start, args=(immediate,), daemon=True
            )
            self.thread.start()

    def update_status(self, text):
        QTimer.singleShot(0, lambda: self.status_label.setText(f"状态：{text}"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebsiteMonitor()
    window.show()
    sys.exit(app.exec())
