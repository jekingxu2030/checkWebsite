import sys
import time
import threading
import requests
import json
from urllib.parse import urlparse

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
)
# from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QTimer#, Qt

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

        # 网站URL输入
        h_layout_url = QHBoxLayout()
        h_layout_url.addWidget(QLabel("监控网站 URL："))
        self.url_input = QLineEdit("https://www.wic-power.com")
        h_layout_url.addWidget(self.url_input)
        layout.addLayout(h_layout_url)

        # 异常检测间隔
        h_layout_interval_err = QHBoxLayout()
        h_layout_interval_err.addWidget(QLabel("异常检测间隔（秒）："))
        self.interval_input_err = QLineEdit("180")
        h_layout_interval_err.addWidget(self.interval_input_err)
        layout.addLayout(h_layout_interval_err)

        # 正常检测间隔
        h_layout_interval_ok = QHBoxLayout()
        h_layout_interval_ok.addWidget(QLabel("正常检测间隔（秒）："))
        self.interval_input_ok = QLineEdit("600")
        h_layout_interval_ok.addWidget(self.interval_input_ok)
        layout.addLayout(h_layout_interval_ok)

        # 钉钉access_token输入
        h_layout_token = QHBoxLayout()
        h_layout_token.addWidget(QLabel("钉钉 access_token："))
        # self.token_input = QLineEdit("aa0366d18f2307daa196c4f96546ed629a92b110448ed104614fe9566dfa1b14")
        self.token_input = QLineEdit("2790e24fa6bb40ba86208e99c4b02223941b51a5b61d0f0e08820d3f461e330d")
        h_layout_token.addWidget(self.token_input)
        layout.addLayout(h_layout_token)

        # 立即检测复选框
        self.check_immediate = QCheckBox("启动后立即检测一次")
        layout.addWidget(self.check_immediate)

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

            immediate = self.check_immediate.isChecked()
            self.thread = threading.Thread(
                target=self.monitor_loop,
                args=(url, interval_err, interval_ok, token, immediate),
                daemon=True
            )
            self.thread.start()

    def monitor_loop(self, url, interval_err, interval_ok, token, immediate):
        first_run = immediate
        # 非首次运行时先等待正常间隔
        if not first_run:
            self.sleep_with_interrupt(interval_ok)
        while not self.stop_event.is_set():
            fault_type = "系统状态"
            status_code = "无"
            try:
                resp = requests.get(url, timeout=10, allow_redirects=True)
                status_code = resp.status_code
                input_domain = urlparse(url).netloc
                resp_domain = urlparse(resp.url).netloc

                if resp.status_code == 200 and input_domain == urlparse(resp.url).netloc:
                    fault_type = "正常"
                    msg = (
                        f"提示：网站正常运行中\n地址：{url}\n状态码：{resp.status_code}\n"
                        f"系统状态：{fault_type}"
                    )
                    self.send_dingding(token, msg, title="系统提醒")
                    self.update_status(f"[正常] 状态码：{resp.status_code}，系统状态：{fault_type}")
                    self.sleep_with_interrupt(interval_ok)
                else:
                    if resp.status_code != 200:
                        if 400 <= resp.status_code < 500:
                            fault_type = f"客户端错误({resp.status_code})"
                            if resp.status_code == 400:
                                hint = "请求参数格式错误，请检查请求内容"
                            elif resp.status_code == 401:
                                hint = "需要身份验证，请检查登录状态或访问令牌"
                            elif resp.status_code == 403:
                                hint = "服务器拒绝访问，请检查权限或IP是否被阻止"
                            elif resp.status_code == 404:
                                hint = "请检查URL是否正确或页面是否已删除"
                            elif resp.status_code == 405:
                                hint = "请求使用的HTTP方法不被服务器允许"
                            elif resp.status_code == 406:
                                hint = "服务器无法提供请求头中指定的格式"
                            elif resp.status_code == 409:
                                hint = "请求与资源当前状态冲突"
                            elif resp.status_code == 408:
                                hint = "服务器等待请求超时，请检查网络连接"
                            elif resp.status_code == 410:
                                hint = "请求的资源已被永久删除，无法恢复"
                            elif resp.status_code == 422:
                                hint = "请求参数格式正确但内容验证失败"
                            elif resp.status_code == 413:
                                hint = "请求体大小超过服务器限制"
                            elif resp.status_code == 414:
                                hint = "请求的URL长度超过服务器允许的限制"
                            elif resp.status_code == 415:
                                hint = "请求的媒体类型不被服务器支持"
                            elif resp.status_code == 421:
                                hint = "请求被发送到无法处理的服务器"
                            elif resp.status_code == 431:
                                hint = "请求头字段大小超过服务器限制"
                            elif resp.status_code == 429:
                                hint = "已超出请求限制，请稍后再试"
                            else:
                                hint = "请求存在错误，请检查请求参数"
                        elif 500 <= resp.status_code < 600:
                            fault_type = f"服务器错误({resp.status_code})"
                            if resp.status_code == 500:
                                hint = "服务器遇到意外错误，请联系管理员"
                            elif resp.status_code == 501:
                                hint = "服务器不支持请求的功能或方法"
                            elif resp.status_code == 502:
                                hint = "服务器作为网关收到无效响应"
                            elif resp.status_code == 503:
                                hint = "服务器暂时无法处理请求，请稍后再试"
                            elif resp.status_code == 504:
                                hint = "服务器作为网关未能及时收到响应"
                            elif resp.status_code == 505:
                                hint = "服务器不支持请求使用的HTTP版本"
                            elif resp.status_code == 506:
                                hint = "服务器内部配置错误导致协商失败"
                            elif resp.status_code == 511:
                                hint = "需要进行网络认证才能访问"
                            else:
                                hint = "服务器处理请求时发生错误，请联系管理员"
                        else:
                            fault_type = f"未知状态码({resp.status_code})"
                            hint = "遇到未知状态码，请检查服务器配置"
                    else:
                        fault_type = f"跳转异常（跳转至{urlparse(resp.url).netloc}）"
                        hint = "请检查网站配置或续费状态。"
                    msg = (
                        f"报警：网站故障\n地址：{url}\n状态码：{resp.status_code}\n"
                        f"故障类型：{fault_type}\n提示：{hint}"
                    )
                    self.send_dingding(token, msg, title="网站报警")
                    self.update_status(f"[异常] 状态码：{resp.status_code}，故障类型：{fault_type}")
                    self.sleep_with_interrupt(interval_err)

                    if input_domain != resp_domain:
                        status_code = resp.status_code
                        fault_type = f"跳转异常（跳转至{resp_domain}）"
                        msg = (
                            f"报警：网站跳转异常\n地址：{url}\n状态码：{status_code}\n跳转地址：{resp.url}\n"
                            f"故障类型：{fault_type}\n提示：请检查网站配置或续费状态。"
                        )
                        self.send_dingding(token, msg, title="网站报警")
                        self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                        self.sleep_with_interrupt(interval_err)

            except requests.exceptions.Timeout:
                status_code = "未知"
                fault_type = "访问超时"
                msg = (
                    f"报警：访问超时\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：请检查网络连接。"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.ConnectionError as e:
                status_code = "未知"
                err_msg = str(e)
                if "Name or service not known" in err_msg or "Temporary failure in name resolution" in err_msg:
                    fault_type = "DNS解析失败"
                elif "Connection refused" in err_msg:
                    fault_type = "地址错误或连接拒绝"
                else:
                    fault_type = "网络连接错误"
                msg = (
                    f"报警：连接错误\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n异常信息：{err_msg}"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.ProxyError:
                status_code = "未知"
                fault_type = "代理服务器错误"
                msg = (
                    f"报警：代理错误\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：请检查代理配置"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.URLRequired:
                status_code = "未知"
                fault_type = "URL缺失"
                msg = (
                    f"报警：URL错误\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：请提供有效的URL地址"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.MissingSchema:
                status_code = "未知"
                fault_type = "URL格式错误"
                msg = (
                    f"报警：URL格式错误\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：URL缺少http://或https://"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.InvalidURL:
                status_code = "未知"
                fault_type = "无效URL"
                msg = (
                    f"报警：URL无效\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：请检查URL格式是否正确"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.SSLError:
                status_code = "未知"
                fault_type = "SSL证书错误"
                msg = (
                    f"报警：SSL证书错误\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：证书无效或已过期"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.ContentDecodingError:
                status_code = "未知"
                fault_type = "内容解码错误"
                msg = (
                    f"报警：内容解码失败\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：服务器返回无法解码的内容"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except requests.exceptions.ChunkedEncodingError:
                status_code = "未知"
                fault_type = "分块编码错误"
                msg = (
                    f"报警：分块编码异常\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：服务器返回无效的分块编码数据"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

            except Exception as e:
                status_code = "未知"
                fault_type = "未知异常"
                msg = (
                    f"报警：未知异常\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n异常信息：{str(e)}"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)

    def sleep_with_interrupt(self, seconds):
        for _ in range(seconds):
            if self.stop_event.is_set():
                break
            time.sleep(1)

    def send_dingding(self, token, message, title="网站报警"):
        webhook = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
        headers = {"Content-Type": "application/json"}
        data = {
            "msgtype": "text",
            "text": {"content": f"【{title}】\n{message}"}
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
