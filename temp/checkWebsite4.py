import sys
import time
import threading
import requests
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
)
from PyQt6.QtCore import QTimer


class WebsiteMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网站可用性监控 - 钉钉推送")
        self.setFixedSize(580, 320)
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
            "aa0366d18f2307daa196c4f96546ed629a92b110448ed104614fe9566dfa1b14"
            # "2790e24fa6bb40ba86208e99c4b02223941b51a5b61d0f0e08820d3f461e330d"
        )
        h_layout_token.addWidget(self.token_input)
        layout.addLayout(h_layout_token)

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
            interval_err = self.interval_input_err.text().strip()
            interval_ok = self.interval_input_ok.text().strip()

            if not url or not token:
                QMessageBox.warning(self, "输入错误", "请填写完整的URL和token")
                return

            try:
                interval_err = int(interval_err)
                interval_ok = int(interval_ok)
                if interval_err < 10 or interval_ok < 10:
                    QMessageBox.warning(self, "输入错误", "检测间隔不能小于10秒")
                    return
            except ValueError:
                QMessageBox.warning(self, "输入错误", "请输入有效的时间间隔（整数）")
                return

            self.monitoring = True
            self.stop_event.clear()
            self.start_btn.setText("停止监控")
            self.update_status(f"开始监控：{url}")

            self.thread = threading.Thread(
                target=self.monitor_loop,
                args=(url, interval_err, interval_ok, token),
                daemon=True,
            )
            self.thread.start()

    def monitor_loop(self, url, interval_err, interval_ok, token):
        while not self.stop_event.is_set():
            fault_type = "系统状态"
            status_code = "无"
            try:
                resp = requests.get(url, timeout=10, allow_redirects=True)
                status_code = resp.status_code
                input_domain = urlparse(url).netloc
                resp_domain = urlparse(resp.url).netloc

                if input_domain != resp_domain:
                    fault_type = f"访问失败"
                    page_title = self.extract_title(resp.text)
                    msg = (
                        f"提示：网站跳转至其他地址\n原始地址：{url}\n跳转后地址：{resp.url}\n"
                        f"状态码：{status_code}\n系统状态：{fault_type}\n信息：{page_title}"
                    )
                    self.send_dingding(token, msg, title="系统报警")
                    self.update_status(
                        f"[跳转] 状态码：{status_code}，信息：{page_title}"
                    )
                    self.sleep_with_interrupt(interval_err)

                elif status_code >= 400:
                    fault_type = f"HTTP错误({status_code})"
                    msg = (
                        f"报警：HTTP状态异常\n地址：{url}\n状态码：{status_code}\n"
                        f"故障类型：{fault_type}\n提示：请尽快处理。"
                    )
                    self.send_dingding(token, msg, title="网站报警")
                    self.update_status(
                        f"[异常] 状态码：{status_code}，故障类型：{fault_type}"
                    )
                    self.sleep_with_interrupt(interval_err)

                else:
                    fault_type = "正常"
                    msg = (
                        f"提示：网站正常运行中\n地址：{url}\n状态码：{status_code}\n"
                        f"系统状态：{fault_type}"
                    )
                    self.send_dingding(token, msg, title="系统提醒")
                    self.update_status(
                        f"[正常] 状态码：{status_code}，系统状态：{fault_type}"
                    )
                    self.sleep_with_interrupt(interval_ok)

            except requests.exceptions.Timeout:
                fault_type = "访问超时"
                msg = f"报警：访问超时\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：请检查网络连接。"
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(
                    f"[异常] 状态码：{status_code}，故障类型：{fault_type}"
                )
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.ConnectionError as e:
                err_msg = str(e)
                if (
                    "Name or service not known" in err_msg
                    or "Temporary failure in name resolution" in err_msg
                ):
                    fault_type = "DNS解析失败"
                elif "Connection refused" in err_msg:
                    fault_type = "地址错误或连接拒绝"
                else:
                    fault_type = "网络连接错误"
                msg = f"报警：连接错误\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n异常信息：{err_msg}"
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(
                    f"[异常] 状态码：{status_code}，故障类型：{fault_type}"
                )
                self.sleep_with_interrupt(interval_err)

            except Exception as e:
                fault_type = "未知异常"
                msg = f"报警：未知异常\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n异常信息：{str(e)}"
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(
                    f"[异常] 状态码：{status_code}，故障类型：{fault_type}"
                )
                self.sleep_with_interrupt(interval_err)

    def sleep_with_interrupt(self, seconds):
        for _ in range(seconds):
            if self.stop_event.is_set():
                break
            time.sleep(1)

    def send_dingding(self, token, message, title="网站报警"):
        webhook = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
        headers = {"Content-Type": "application/json"}
        data = {"msgtype": "text", "text": {"content": f"【{title}】\n{message}"}}
        try:
            response = requests.post(webhook, headers=headers, data=json.dumps(data))
            print(f"[推送结果] {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[推送失败] {e}")

    def update_status(self, text):
        QTimer.singleShot(0, lambda: self.status_label.setText(f"状态：{text}"))

    def extract_title(self, html):
        try:
            soup = BeautifulSoup(html, "html.parser")
            return (
                soup.title.string.strip()
                if soup.title and soup.title.string
                else "(无标题)"
            )
        except Exception:
            return "(无法提取标题)"


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebsiteMonitor()
    window.show()
    sys.exit(app.exec())
