#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网站可用性监控工具 - 钉钉推送版
功能: 监控指定网站的可用性，检测状态码、域名跳转及核心index文件访问情况，异常时通过钉钉机器人推送报警信息
"""
import sys
import time
import threading
import requests  # 用于发送HTTP请求
import json      # 用于处理JSON数据
from urllib.parse import urlparse, urljoin  # 用于解析URL域名和拼接URL

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
)
# from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QTimer  # , Qt


class WebsiteMonitor(QWidget):
    """
    网站监控主窗口类
    负责UI界面构建、监控线程管理和状态显示
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网站可用性监控 - 钉钉推送")
        self.setFixedSize(580, 320)
        self.monitoring = False  # 监控状态标志
        self.stop_event = threading.Event()  # 线程停止事件
        self.thread = None  # 监控线程对象
        self.init_ui()  # 初始化UI界面

    def update_status(self, message):
        """更新UI状态标签"""
        self.status_label.setText(f"状态：{message}")

    def init_ui(self):
        """
        初始化用户界面
        创建并排列所有UI控件：输入框、复选框、状态标签和控制按钮
        """
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
        self.token_input = QLineEdit(
            "2790e24fa6bb40ba86208e99c4b02223941b51a5b61d0f0e08820d3f461e330d")
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
        """
        切换监控状态（开始/停止监控）
        - 停止监控：设置标志位、触发事件、更新UI状态
        - 开始监控：验证输入参数、初始化线程并启动监控循环
        """
        if self.monitoring:
            # 停止监控逻辑
            self.monitoring = False
            self.stop_event.set()
            self.start_btn.setText("开始监控")
            self.update_status("已停止监控")
        else:
            # 获取并验证输入参数
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
        """
        监控主循环 - 周期性检测网站状态
        参数:
            url: 监控目标URL
            interval_err: 异常时检测间隔(秒)
            interval_ok: 正常时检测间隔(秒)
            token: 钉钉机器人token
            immediate: 是否立即执行首次检测
        逻辑流程:
            1. 处理首次检测逻辑
            2. 循环执行网站健康检查
            3. 根据检测结果(状态码/跳转/index文件)判断网站状态
            4. 异常时发送钉钉报警并使用异常间隔
            5. 正常时发送状态通知并使用正常间隔
        """
        first_run = immediate  # 是否立即执行首次检测
        # 非首次运行时先等待正常间隔
        if not first_run:
            self.sleep_with_interrupt(interval_ok)
        while not self.stop_event.is_set():
            fault_type = "系统状态"
            status_code = "无"
            try:
                input_domain = urlparse(url).netloc
                # 检查多个关键路径是否有任意一个返回200且域名未跳转
                # 包含根路径、常见首页文件和健康检查接口
                paths_to_check = ['','index.html', 'index.htm']  # 仅检查根路径
                any_200 = False
                resp_status_code = 0
                resp_domain = input_domain

                for path in paths_to_check:
                    try:
                        # 安全拼接URL，避免双斜杠问题
                        full_url = urljoin(url, path)
                        # 发送请求，允许重定向，超时10秒
                        path_resp = requests.get(full_url, timeout=10, allow_redirects=True)
                        current_domain = urlparse(path_resp.url).netloc
                    
                        # 检查状态码和域名跳转
                        if path_resp.status_code == 200 and current_domain == input_domain:
                                any_200 = True
                                resp_status_code = path_resp.status_code
                                resp_domain = current_domain
                                break  # 找到有效路径后退出循环
                    except requests.RequestException:
                        continue  # 请求失败则尝试下一个路径

            # 所有路径都失败时触发连接错误
            if not any_200 and resp_status_code == 0:
                raise requests.exceptions.ConnectionError("所有路径请求失败")

            # 分支1：返回200且未跳转其他地址
            if resp_status_code == 200 and resp_domain == input_domain:
                fault_type = "正常"
                if 'hint' not in locals():
                    hint = ''
                msg = (
                    f"提示：网站正常运行中\n地址：{url}\n状态码：{resp_status_code}\n"
                    f"系统状态：{fault_type}"
                )
                self.send_dingding(token, msg, title="系统提醒")
                self.update_status(
                f"[正常] 状态码：{resp_status_code}，系统状态：{fault_type}")
                self.sleep_with_interrupt(interval_ok)
            # 分支2：根地址跳转到其他地址
            elif resp_domain != input_domain:
                fault_type = "根地址跳转到其他地址"
                msg = (
                    f"报警：根地址跳转到其他域名\n地址：{url}\n原域名：{input_domain}\n跳转后域名：{resp_domain}\n状态码：{resp_status_code}"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(f"[异常] 根地址跳转到{resp_domain}，状态码：{resp_status_code}")
                self.sleep_with_interrupt(interval_err)
            # 分支3：其余状态码（未跳转但状态码非200）
            elif resp_status_code != 200:
                if 400 <= resp_status_code < 500:
                    fault_type = f"客户端错误({resp_status_code})"
                    if resp_status_code == 400:
                        hint = "请求参数格式错误，请检查请求内容"
                    elif resp_status_code == 401:
                        hint = "需要身份验证，请检查登录状态或访问令牌"
                    elif resp_status_code == 403:
                        hint = "服务器拒绝访问，请检查权限或IP是否被阻止"
                    elif resp_status_code == 404:
                        hint = "请检查URL是否正确或页面是否已删除"
                    elif resp_status_code == 405:
                        hint = "请求使用的HTTP方法不被服务器允许"
                    elif resp_status_code == 406:
                        hint = "服务器无法提供请求头中指定的格式"
                    elif resp_status_code == 409:
                        hint = "请求与资源当前状态冲突"
                    elif resp_status_code == 408:
                        hint = "服务器等待请求超时，请检查网络连接"
                    elif resp_status_code == 410:
                        hint = "请求的资源已被永久删除，无法恢复"
                    elif resp_status_code == 422:
                        hint = "请求参数格式正确但内容验证失败"
                    elif resp_status_code == 413:
                        hint = "请求体大小超过服务器限制"
                    elif resp_status_code == 414:
                        hint = "请求的URL长度超过服务器允许的限制"
                    elif resp_status_code == 415:
                        hint = "请求的媒体类型不被服务器支持"
                    elif resp_status_code == 421:
                        hint = "请求被发送到无法处理的服务器"
                    elif resp_status_code == 431:
                        hint = "请求头字段大小超过服务器限制"
                    elif resp_status_code == 429:
                        hint = "已超出请求限制，请稍后再试"
                elif 500 <= resp_status_code < 600:
                    fault_type = f"服务器错误({resp_status_code})"
                    if resp_status_code == 500:
                        hint = "服务器遇到意外错误，请联系管理员"
                    elif resp_status_code == 501:
                        hint = "服务器不支持请求的功能或方法"
                    elif resp_status_code == 502:
                        hint = "服务器作为网关收到无效响应"
                    elif resp_status_code == 503:
                        hint = "服务器暂时无法处理请求，请稍后再试"
                    elif resp_status_code == 504:
                        hint = "服务器作为网关未能及时收到响应"
                    elif resp_status_code == 505:
                        hint = "服务器不支持请求使用的HTTP版本"
                    elif resp_status_code == 506:
                        hint = "服务器内部配置错误导致协商失败"
                    elif resp_status_code == 511:
                        hint = "需要进行网络认证才能访问"
                else:
                    fault_type = f"未知状态码({resp_status_code})"
                    hint = "遇到未知状态码，请检查服务器配置"
                # 假设 is_redirect 变量已定义，此处原代码未定义该变量，需检查逻辑
                # elif is_redirect: 暂时注释，需补充逻辑
                #     fault_type = f"跳转异常（跳转至{urlparse(resp.url).netloc}）"
                #     hint = "请检查网站配置或续费状态。"

                msg = (
                    f"报警：网站故障\n地址：{url}\n状态码：{resp_status_code}\n"
                    f"故障类型：{fault_type}\n提示：{hint}"
                )
                self.send_dingding(token, msg, title="网站报警")
                self.update_status(
                    f"[异常] 状态码：{resp_status_code}，故障类型：{fault_type}")
                self.sleep_with_interrupt(interval_err)



        except requests.exceptions.Timeout:
            # 请求超时：服务器在规定时间内未响应（10秒超时）
            status_code = "未知"
            fault_type = "访问超时"
            msg = (
                f"报警：访问超时\n地址：{url}\n状态码：{status_code}\n故障类型：{fault_type}\n提示：请检查网络连接。"
            )
            self.send_dingding(token, msg, title="网站报警")
            self.update_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")
            self.sleep_with_interrupt(interval_err)

        except requests.exceptions.ConnectionError as e:
            # 连接错误：处理TCP连接失败场景，细分错误类型
            status_code = "未知"
            err_msg = str(e)
            # 根据错误信息分类：DNS解析失败/连接拒绝/其他连接错误
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

    def send_dingding(self, token, content, title="网站监控报警"):
        """
        发送钉钉机器人消息
        参数:
            token: 钉钉机器人access_token
            content: 消息内容
            title: 消息标题
        """
        url = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "msgtype": "text",
            "text": {
                "content": f"{title}\n{content}"
            }
        }
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"钉钉消息发送失败: {str(e)}")
            return False

    def sleep_with_interrupt(self, seconds):
        """
        可中断的睡眠函数
        实现线程安全的间隔等待，支持通过stop_event随时中断
        参数: seconds - 计划睡眠秒数
        逻辑: 每秒检查一次停止事件，若触发则提前退出
        """
        for _ in range(seconds):
            if self.stop_event.is_set():
                break
            time.sleep(1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebsiteMonitor()
    window.show()
    sys.exit(app.exec())
