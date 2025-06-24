import sys
import time
import threading
import requests
import json

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import QTimer


class WebsiteMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网站可用性监控 - 钉钉推送")
        self.setFixedSize(520, 240)
        self.monitoring = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 网站URL输入
        h_layout_url = QHBoxLayout()
        h_layout_url.addWidget(QLabel("监控网站 URL："))
        self.url_input = QLineEdit("https://www.wic-power.com")
        h_layout_url.addWidget(self.url_input)
        layout.addLayout(h_layout_url)

        # 时间间隔输入
        h_layout_interval = QHBoxLayout()
        h_layout_interval.addWidget(QLabel("检测间隔（秒）："))
        self.interval_input = QLineEdit("180")
        h_layout_interval.addWidget(self.interval_input)
        layout.addLayout(h_layout_interval)

        # 状态显示标签
        self.status_label = QLabel("状态：未开始监控")
        layout.addWidget(self.status_label)

        # 控制按钮
        self.start_btn = QPushButton("开始监控")
        self.start_btn.clicked.connect(self.toggle_monitoring)
        layout.addWidget(self.start_btn)

        self.setLayout(layout)

    def toggle_monitoring(self):
        if self.monitoring:
            self.monitoring = False
            self.start_btn.setText("开始监控")
            self.update_status("已停止监控")
        else:
            url = self.url_input.text().strip()
            interval = self.interval_input.text().strip()

            if not url:
                QMessageBox.warning(self, "输入错误", "请填写完整的网站URL")
                return

            try:
                interval_sec = int(interval)
                if interval_sec < 10:
                    QMessageBox.warning(self, "输入错误", "检测间隔不能小于10秒")
                    return
            except ValueError:
                QMessageBox.warning(self, "输入错误", "请输入有效的时间间隔（整数）")
                return

            self.monitoring = True
            self.start_btn.setText("停止监控")
            self.update_status(f"开始监控：{url} 每 {interval_sec} 秒检测一次")

            thread = threading.Thread(
                target=self.monitor_loop,
                args=(url, interval_sec),
                daemon=True
            )
            thread.start()

    def monitor_loop(self, url, interval):
        token = "aa0366d18f2307daa196c4f96546ed629a92b110448ed104614fe9566dfa1b14"
        while self.monitoring:
            try:
                resp = requests.get(url, timeout=10)
                status_code = resp.status_code
                if status_code != 200:
                    msg = f"报警：网站故障\n地址：{url}\n状态码：{status_code}\n提示：请尽快处理。"
                    self.send_dingding(token, msg)
                    self.update_status(f"[异常] 状态码：{status_code}")
                else:
                    self.update_status(f"[正常] 状态码：{status_code}")
            except Exception as e:
                msg = f"报警：网站请求失败\n地址：{url}\n提示：异常信息：{str(e)}"
                self.send_dingding(token, msg)
                self.update_status(f"[异常] 请求失败：{e}")
            time.sleep(interval)

    def send_dingding(self, token, message):
        webhook = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
        headers = {"Content-Type": "application/json"}
        data = {
            "msgtype": "text",
            "text": {"content": message}
        }
        try:
            response = requests.post(webhook, headers=headers, data=json.dumps(data))
            print(f"[推送结果] {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[推送失败] {e}")

    def update_status(self, text):
        QTimer.singleShot(0, lambda: self.status_label.setText(f"状态：{text}"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebsiteMonitor()
    window.show()
    sys.exit(app.exec())
