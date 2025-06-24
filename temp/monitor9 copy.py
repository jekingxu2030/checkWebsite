# # # monitor.py
# # import time
# # import json
# # import requests
# # from urllib.parse import urlparse, urljoin


# # class Monitor:
# #     def __init__(
# #         self, url, token, interval_ok, interval_err, callback_status, stop_event
# #     ):
# #         self.url = url
# #         self.token = token
# #         self.interval_ok = interval_ok
# #         self.interval_err = interval_err
# #         self.callback_status = callback_status
# #         self.stop_event = stop_event

# #     def start(self, immediate=True):
# #         first_run = immediate
# #         if not first_run:
# #             self.sleep_with_interrupt(self.interval_ok)

# #         while not self.stop_event.is_set():
# #             try:
# #                 self.check_website()
# #             except Exception as e:
# #                 self.handle_exception("未知异常", str(e))
# #                 self.sleep_with_interrupt(self.interval_err)

# #     def check_website(self):
# #         input_domain = urlparse(self.url).netloc
# #         paths_to_check = ["", "index.html", "index.htm"]
# #         resp_status_code = 0
# #         resp_domain = input_domain

# #         for path in paths_to_check:
# #             try:
# #                 full_url = urljoin(self.url, path)
# #                 path_resp = requests.get(full_url, timeout=10, allow_redirects=True)
# #                 current_domain = urlparse(path_resp.url).netloc
# #                 if path_resp.status_code == 200 and current_domain == input_domain:
# #                     self.report_ok(path_resp.status_code)
# #                     self.sleep_with_interrupt(self.interval_ok)
# #                     return
# #                 resp_status_code = path_resp.status_code
# #                 resp_domain = current_domain
# #             except requests.RequestException:
# #                 continue

# #         if resp_domain != input_domain:
# #             self.report_issue(
# #                 "根地址跳转到其他域名",
# #                 f"原域名：{input_domain}\n跳转后域名：{resp_domain}\n状态码：{resp_status_code}",
# #             )
# #         elif resp_status_code != 200:
# #             self.handle_http_status(resp_status_code)
# #         self.sleep_with_interrupt(self.interval_err)

# #     def report_ok(self, code):
# #         msg = f"提示：网站正常运行中\n地址：{self.url}\n状态码：{code}\n系统状态：正常"
# #         self.send_dingding(msg, title="系统提醒")
# #         self.callback_status(f"[正常] 状态码：{code}，系统状态：正常")

# #     def handle_http_status(self, code):
# #         if 400 <= code < 500:
# #             fault = f"客户端错误({code})"
# #         elif 500 <= code < 600:
# #             fault = f"服务器错误({code})"
# #         else:
# #             fault = f"未知状态码({code})"
# #         self.report_issue(fault, f"地址：{self.url}\n状态码：{code}")

# #     def report_issue(self, fault_type, message):
# #         full_msg = f"报警：网站故障\n{message}\n故障类型：{fault_type}"
# #         self.send_dingding(full_msg)
# #         self.callback_status(f"[异常] {fault_type}")

# #     def send_dingding(self, message, title="网站报警"):
# #         webhook = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}"
# #         headers = {"Content-Type": "application/json"}
# #         data = {"msgtype": "text", "text": {"content": f"【{title}】\n{message}"}}
# #         try:
# #             requests.post(webhook, headers=headers, data=json.dumps(data))
# #         except Exception as e:
# #             print(f"[推送失败] {e}")

# #     def handle_exception(self, fault_type, error_msg):
# #         msg = f"报警：{fault_type}\n地址：{self.url}\n异常信息：{error_msg}"
# #         self.send_dingding(msg)
# #         self.callback_status(f"[异常] {fault_type}：{error_msg}")

# #     def sleep_with_interrupt(self, seconds):
# #         for _ in range(seconds):
# #             if self.stop_event.is_set():
# #                 break
# #             time.sleep(1)
# import time
# import json
# import requests
# from urllib.parse import urlparse, urljoin


# class Monitor:
#     def __init__(
#         self, url, token, interval_ok, interval_err, callback_status, stop_event
#     ):
#         self.url = url
#         self.token = token
#         self.interval_ok = interval_ok
#         self.interval_err = interval_err
#         self.callback_status = callback_status
#         self.stop_event = stop_event

#     def start(self, immediate=True):
#         first_run = immediate
#         if not first_run:
#             self.sleep_with_interrupt(self.interval_ok)

#         while not self.stop_event.is_set():
#             try:
#                 self.check_website()
#             except Exception as e:
#                 self.handle_exception("未知异常", str(e))
#                 self.sleep_with_interrupt(self.interval_err)

#     def check_website(self):
#         input_domain = urlparse(self.url).netloc
#         paths_to_check = [""]
#         resp_status_code = 0
#         resp_domain = input_domain

#         for path in paths_to_check:
#             try:
#                 full_url = urljoin(self.url, path)
#                 path_resp = requests.get(full_url, timeout=10, allow_redirects=True)
#                 current_domain = urlparse(path_resp.url).netloc
#                 resp_status_code = path_resp.status_code
#                 resp_domain = current_domain

#                 if resp_status_code == 200 and current_domain == input_domain:
#                     self.report_ok(resp_status_code)
#                     self.sleep_with_interrupt(self.interval_ok)
#                     return
#             except requests.RequestException:
#                 continue

#         if resp_domain != input_domain:
#             fault_type = "根地址跳转到其他域名"
#             msg = f"报警：根地址跳转到其他域名\n地址：{self.url}\n原域名：{input_domain}\n跳转后域名：{resp_domain}\n状态码：{resp_status_code}"
#             self.send_dingding(msg)
#             self.callback_status(f"[异常] {fault_type}，状态码：{resp_status_code}")
#         else:
#             fault_type, hint = self.analyze_status_code(resp_status_code)
#             msg = f"报警：网站故障\n地址：{self.url}\n状态码：{resp_status_code}\n故障类型：{fault_type}\n提示：{hint}"
#             self.send_dingding(msg)
#             self.callback_status(
#                 f"[异常] 状态码：{resp_status_code}，故障类型：{fault_type}"
#             )

#         self.sleep_with_interrupt(self.interval_err)

#     def analyze_status_code(self, code):
#         hint = "未知错误"
#         if 400 <= code < 500:
#             fault = f"客户端错误({code})"
#             hints = {
#                 400: "请求参数格式错误，请检查请求内容",
#                 401: "需要身份验证，请检查登录状态或访问令牌",
#                 403: "服务器拒绝访问，请检查权限或IP是否被阻止",
#                 404: "请检查URL是否正确或页面是否已删除",
#                 405: "请求使用的HTTP方法不被服务器允许",
#                 406: "服务器无法提供请求头中指定的格式",
#                 408: "服务器等待请求超时，请检查网络连接",
#                 409: "请求与资源当前状态冲突",
#                 410: "请求的资源已被永久删除，无法恢复",
#                 413: "请求体大小超过服务器限制",
#                 414: "请求的URL长度超过服务器允许的限制",
#                 415: "请求的媒体类型不被服务器支持",
#                 421: "请求被发送到无法处理的服务器",
#                 422: "请求参数格式正确但内容验证失败",
#                 429: "已超出请求限制，请稍后再试",
#                 431: "请求头字段大小超过服务器限制",
#             }
#             hint = hints.get(code, hint)
#         elif 500 <= code < 600:
#             fault = f"服务器错误({code})"
#             hints = {
#                 500: "服务器遇到意外错误，请联系管理员",
#                 501: "服务器不支持请求的功能或方法",
#                 502: "服务器作为网关收到无效响应",
#                 503: "服务器暂时无法处理请求，请稍后再试",
#                 504: "服务器作为网关未能及时收到响应",
#                 505: "服务器不支持请求使用的HTTP版本",
#                 506: "服务器内部配置错误导致协商失败",
#                 511: "需要进行网络认证才能访问",
#             }
#             hint = hints.get(code, hint)
#         else:
#             fault = f"未知状态码({code})"
#             hint = "遇到未知状态码，请检查服务器配置"

#         return fault, hint

#     def report_ok(self, code):
#         msg = f"提示：网站正常运行中\n地址：{self.url}\n状态码：{code}\n系统状态：正常"
#         self.send_dingding(msg, title="系统提醒")
#         self.callback_status(f"[正常] 状态码：{code}，系统状态：正常")

#     def send_dingding(self, message, title="网站报警"):
#         webhook = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}"
#         headers = {"Content-Type": "application/json"}
#         data = {"msgtype": "text", "text": {"content": f"【{title}】\n{message}"}}
#         try:
#             requests.post(webhook, headers=headers, data=json.dumps(data))
#         except Exception as e:
#             print(f"[推送失败] {e}")

#     def handle_exception(self, fault_type, error_msg):
#         msg = f"报警：{fault_type}\n地址：{self.url}\n异常信息：{error_msg}"
#         self.send_dingding(msg)
#         self.callback_status(f"[异常] {fault_type}：{error_msg}")

#     def sleep_with_interrupt(self, seconds):
#         for _ in range(seconds):
#             if self.stop_event.is_set():
#                 break
#             time.sleep(1)
# # import time
# # import json
# # import requests
# # from urllib.parse import urlparse, urljoin


# # class Monitor:
# #     def __init__(
# #         self, url, token, interval_ok, interval_err, callback_status, stop_event
# #     ):
# #         self.url = url
# #         self.token = token
# #         self.interval_ok = interval_ok
# #         self.interval_err = interval_err
# #         self.callback_status = callback_status
# #         self.stop_event = stop_event

# #     def start(self, immediate=True):
# #         first_run = immediate
# #         if not first_run:
# #             self.sleep_with_interrupt(self.interval_ok)

# #         while not self.stop_event.is_set():
# #             try:
# #                 self.check_website()
# #             except Exception as e:
# #                 self.handle_exception("未知异常", str(e))
# #                 self.sleep_with_interrupt(self.interval_err)

# #     def check_website(self):
# #         input_domain = urlparse(self.url).netloc
# #         paths_to_check = [""]
# #         resp_status_code = 0
# #         resp_domain = input_domain

# #         for path in paths_to_check:
# #             full_url = urljoin(self.url, path)
# #             try:
# #                 path_resp = requests.get(full_url, timeout=10, allow_redirects=True)
# #                 current_domain = urlparse(path_resp.url).netloc
# #                 resp_status_code = path_resp.status_code
# #                 resp_domain = current_domain

# #                 if resp_status_code == 200 and current_domain == input_domain:
# #                     self.report_ok(resp_status_code)
# #                     self.sleep_with_interrupt(self.interval_ok)
# #                     return
# #             except requests.RequestException as e:
# #                 self.handle_exception("请求异常", str(e))
# #                 self.sleep_with_interrupt(self.interval_err)
# #                 return

# #         if resp_domain != input_domain:
# #             fault_type = "根地址跳转到其他域名"
# #             msg = (
# #                 f"报警：根地址跳转到其他域名\n地址：{self.url}\n原域名：{input_domain}\n"
# #                 f"跳转后域名：{resp_domain}\n状态码：{resp_status_code}"
# #             )
# #             self.send_dingding(msg)
# #             self.callback_status(f"[异常] {fault_type}，状态码：{resp_status_code}")
# #         else:
# #             if resp_status_code == 0:
# #                 fault_type = "请求失败"
# #                 hint = "无法获取有效状态码，请检查网络或URL是否正确"
# #                 msg = (
# #                     f"报警：网站故障\n地址：{self.url}\n状态码：{resp_status_code}\n"
# #                     f"故障类型：{fault_type}\n提示：{hint}"
# #                 )
# #                 self.send_dingding(msg)
# #                 self.callback_status(
# #                     f"[异常] 状态码：{resp_status_code}，故障类型：{fault_type}"
# #                 )
# #             else:
# #                 fault_type, hint = self.analyze_status_code(resp_status_code)
# #                 msg = (
# #                     f"报警：网站故障\n地址：{self.url}\n状态码：{resp_status_code}\n"
# #                     f"故障类型：{fault_type}\n提示：{hint}"
# #                 )
# #                 self.send_dingding(msg)
# #                 self.callback_status(
# #                     f"[异常] 状态码：{resp_status_code}，故障类型：{fault_type}"
# #                 )

# #         self.sleep_with_interrupt(self.interval_err)

# #     def analyze_status_code(self, code):
# #         hint = "未知错误"
# #         if 400 <= code < 500:
# #             fault = f"客户端错误({code})"
# #             hints = {
# #                 400: "请求参数格式错误，请检查请求内容",
# #                 401: "需要身份验证，请检查登录状态或访问令牌",
# #                 403: "服务器拒绝访问，请检查权限或IP是否被阻止",
# #                 404: "请检查URL是否正确或页面是否已删除",
# #                 405: "请求使用的HTTP方法不被服务器允许",
# #                 406: "服务器无法提供请求头中指定的格式",
# #                 408: "服务器等待请求超时，请检查网络连接",
# #                 409: "请求与资源当前状态冲突",
# #                 410: "请求的资源已被永久删除，无法恢复",
# #                 413: "请求体大小超过服务器限制",
# #                 414: "请求的URL长度超过服务器允许的限制",
# #                 415: "请求的媒体类型不被服务器支持",
# #                 421: "请求被发送到无法处理的服务器",
# #                 422: "请求参数格式正确但内容验证失败",
# #                 429: "已超出请求限制，请稍后再试",
# #                 431: "请求头字段大小超过服务器限制",
# #             }
# #             hint = hints.get(code, hint)
# #         elif 500 <= code < 600:
# #             fault = f"服务器错误({code})"
# #             hints = {
# #                 500: "服务器遇到意外错误，请联系管理员",
# #                 501: "服务器不支持请求的功能或方法",
# #                 502: "服务器作为网关收到无效响应",
# #                 503: "服务器暂时无法处理请求，请稍后再试",
# #                 504: "服务器作为网关未能及时收到响应",
# #                 505: "服务器不支持请求使用的HTTP版本",
# #                 506: "服务器内部配置错误导致协商失败",
# #                 511: "需要进行网络认证才能访问",
# #             }
# #             hint = hints.get(code, hint)
# #         else:
# #             fault = f"未知状态码({code})"
# #             hint = "遇到未知状态码，请检查服务器配置"

# #         return fault, hint

# #     def report_ok(self, code):
# #         msg = f"提示：网站正常运行中\n地址：{self.url}\n状态码：{code}\n系统状态：正常"
# #         self.send_dingding(msg, title="系统提醒")
# #         self.callback_status(f"[正常] 状态码：{code}，系统状态：正常")

# #     def send_dingding(self, message, title="网站报警"):
# #         webhook = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}"
# #         headers = {"Content-Type": "application/json"}
# #         data = {"msgtype": "text", "text": {"content": f"【{title}】\n{message}"}}
# #         try:
# #             requests.post(webhook, headers=headers, data=json.dumps(data))
# #         except Exception as e:
# #             print(f"[推送失败] {e}")

# #     def handle_exception(self, fault_type, error_msg):
# #         msg = f"报警：{fault_type}\n地址：{self.url}\n异常信息：{error_msg}"
# #         self.send_dingding(msg)
# #         self.callback_status(f"[异常] {fault_type}：{error_msg}")

# #     def sleep_with_interrupt(self, seconds):
# #         for _ in range(seconds):
# #             if self.stop_event.is_set():
# #                 break
# #             time.sleep(1)
# import time
# import json
# import requests
# from urllib.parse import urlparse, urljoin


# class Monitor:
#     def __init__(
#         self, url, token, interval_ok, interval_err, callback_status, stop_event
#     ):
#         self.url = url
#         self.token = token
#         self.interval_ok = interval_ok
#         self.interval_err = interval_err
#         self.callback_status = callback_status
#         self.stop_event = stop_event

#     def start(self, immediate=True):
#         first_run = immediate
#         if not first_run:
#             self.sleep_with_interrupt(self.interval_ok)

#         while not self.stop_event.is_set():
#             try:
#                 self.check_website()
#             except Exception as e:
#                 self.handle_exception("未知异常", str(e))
#                 self.sleep_with_interrupt(self.interval_err)

#     def check_website(self):
#         input_domain = urlparse(self.url).netloc
#         paths_to_check = [""]
#         resp_status_code = None
#         resp_domain = input_domain

#         for path in paths_to_check:
#             try:
#                 full_url = urljoin(self.url, path)
#                 path_resp = requests.get(full_url, timeout=10, allow_redirects=True)
#                 current_domain = urlparse(path_resp.url).netloc
#                 resp_status_code = path_resp.status_code
#                 resp_domain = current_domain

#                 # 第一类：200状态且无跳转根域名
#                 if resp_status_code == 200 and current_domain == input_domain:
#                     self.report_ok(resp_status_code)
#                     self.sleep_with_interrupt(self.interval_ok)
#                     return
#             except requests.exceptions.Timeout:
#                 self.handle_timeout()
#                 self.sleep_with_interrupt(self.interval_err)
#                 return
#             except requests.RequestException as e:
#                 # 这里捕获其他请求异常，继续尝试或后续处理
#                 continue

#         # 第二类：跳转到其他根域名
#         if resp_domain != input_domain and resp_status_code is not None:
#             fault_type = "根地址跳转到其他域名"
#             msg = (
#                 f"报警：根地址跳转到其他域名\n地址：{self.url}\n原域名：{input_domain}\n"
#                 f"跳转后域名：{resp_domain}\n状态码：{resp_status_code}"
#             )
#             self.send_dingding(msg)
#             self.callback_status(f"[异常] {fault_type}，状态码：{resp_status_code}")
#         else:
#             # 第三类：异常状态，分析状态码
#             if resp_status_code is None:
#                 # 没有响应状态码，视为连接异常
#                 fault_type = "请求异常"
#                 hint = "无法获取响应状态码，可能网络连接异常"
#                 msg = (
#                     f"报警：{fault_type}\n地址：{self.url}\n异常信息：无响应状态码，"
#                     "可能DNS解析失败或服务器无响应"
#                 )
#                 self.send_dingding(msg)
#                 self.callback_status(f"[异常] {fault_type}：{hint}")
#             else:
#                 fault_type, hint = self.analyze_status_code(resp_status_code)
#                 msg = (
#                     f"报警：网站故障\n地址：{self.url}\n状态码：{resp_status_code}\n"
#                     f"故障类型：{fault_type}\n提示：{hint}"
#                 )
#                 self.send_dingding(msg)
#                 self.callback_status(
#                     f"[异常] 状态码：{resp_status_code}，故障类型：{fault_type}"
#                 )
#         self.sleep_with_interrupt(self.interval_err)

#     def analyze_status_code(self, code):
#         hint = "未知错误"
#         if 400 <= code < 500:
#             fault = f"客户端错误({code})"
#             hints = {
#                 400: "请求参数格式错误，请检查请求内容",
#                 401: "需要身份验证，请检查登录状态或访问令牌",
#                 403: "服务器拒绝访问，请检查权限或IP是否被阻止",
#                 404: "请检查URL是否正确或页面是否已删除",
#                 405: "请求使用的HTTP方法不被服务器允许",
#                 406: "服务器无法提供请求头中指定的格式",
#                 408: "服务器等待请求超时，请检查网络连接",
#                 409: "请求与资源当前状态冲突",
#                 410: "请求的资源已被永久删除，无法恢复",
#                 413: "请求体大小超过服务器限制",
#                 414: "请求的URL长度超过服务器允许的限制",
#                 415: "请求的媒体类型不被服务器支持",
#                 421: "请求被发送到无法处理的服务器",
#                 422: "请求参数格式正确但内容验证失败",
#                 429: "已超出请求限制，请稍后再试",
#                 431: "请求头字段大小超过服务器限制",
#             }
#             hint = hints.get(code, hint)
#         elif 500 <= code < 600:
#             fault = f"服务器错误({code})"
#             hints = {
#                 500: "服务器遇到意外错误，请联系管理员",
#                 501: "服务器不支持请求的功能或方法",
#                 502: "服务器作为网关收到无效响应",
#                 503: "服务器暂时无法处理请求，请稍后再试",
#                 504: "服务器作为网关未能及时收到响应",
#                 505: "服务器不支持请求使用的HTTP版本",
#                 506: "服务器内部配置错误导致协商失败",
#                 511: "需要进行网络认证才能访问",
#             }
#             hint = hints.get(code, hint)
#         else:
#             fault = f"未知状态码({code})"
#             hint = "遇到未知状态码，请检查服务器配置"

#         return fault, hint

#     def report_ok(self, code):
#         msg = f"提示：网站正常运行中\n地址：{self.url}\n状态码：{code}\n系统状态：正常"
#         self.send_dingding(msg, title="系统提醒")
#         self.callback_status(f"[正常] 状态码：{code}，系统状态：正常")

#     def handle_timeout(self):
#         status_code = "未知"
#         fault_type = "访问超时"
#         msg = (
#             f"报警：访问超时\n地址：{self.url}\n状态码：{status_code}\n"
#             f"故障类型：{fault_type}\n提示：请检查网络连接。"
#         )
#         self.send_dingding(msg)
#         self.callback_status(f"[异常] 状态码：{status_code}，故障类型：{fault_type}")

#     def send_dingding(self, message, title="网站报警"):
#         webhook = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}"
#         headers = {"Content-Type": "application/json"}
#         data = {"msgtype": "text", "text": {"content": f"【{title}】\n{message}"}}
#         try:
#             requests.post(webhook, headers=headers, data=json.dumps(data))
#         except Exception as e:
#             print(f"[推送失败] {e}")

#     def handle_exception(self, fault_type, error_msg):
#         msg = f"报警：{fault_type}\n地址：{self.url}\n异常信息：{error_msg}"
#         self.send_dingding(msg)
#         self.callback_status(f"[异常] {fault_type}：{error_msg}")

#     def sleep_with_interrupt(self, seconds):
#         for _ in range(seconds):
#             if self.stop_event.is_set():
#                 break
#             time.sleep(1)


import time
import json
import requests
from urllib.parse import urlparse, urljoin


class Monitor:
    def __init__(
        self, url, token, interval_ok, interval_err, callback_status, stop_event
    ):
        self.url = url
        self.token = token
        self.interval_ok = interval_ok
        self.interval_err = interval_err
        self.callback_status = callback_status
        self.stop_event = stop_event

    def start(self, immediate=True):
        first_run = immediate
        if not first_run:
            self.sleep_with_interrupt(self.interval_ok)

        while not self.stop_event.is_set():
            try:
                self.check_website()
            except Exception as e:
                self.handle_exception("请求异常", str(e))
                self.sleep_with_interrupt(self.interval_err)

    def check_website(self):
        input_domain = urlparse(self.url).netloc
        paths_to_check = [""]  # 只检测根路径
        resp_status_code = None
        resp_domain = input_domain

        for path in paths_to_check:
            try:
                full_url = urljoin(self.url, path)
                path_resp = requests.get(full_url, timeout=10, allow_redirects=True)
                current_domain = urlparse(path_resp.url).netloc
                resp_status_code = path_resp.status_code
                resp_domain = current_domain

                if resp_status_code == 200 and current_domain == input_domain:
                    self.report_ok(resp_status_code)
                    self.sleep_with_interrupt(self.interval_ok)
                    return
            except requests.RequestException:
                continue

        if resp_domain != input_domain:
            fault_type = "根地址跳转到其他域名"
            msg = (
                f"报警：根地址跳转到其他域名\n地址：{self.url}\n原域名：{input_domain}"
                f"\n跳转后域名：{resp_domain}\n状态码：{resp_status_code}"
            )
            self.send_dingding(msg)
            self.callback_status(f"[异常] {fault_type}，状态码：{resp_status_code}")
        else:
            if resp_status_code is None:
                # 无响应状态码，认为是超时或无响应
                fault_type = "无响应状态码"
                timeout_hint = "无响应状态码，可能DNS解析失败或服务器无响应"
                self.send_dingding(
                    timeout_hint,
                    fault_type=fault_type,
                    error_msg=None,
                )
                self.callback_status(f"[异常] {fault_type}，提示：{timeout_hint}")
            else:
                fault_type, hint = self.analyze_status_code(resp_status_code)
                self.send_dingding(
                    f"报警：网站故障\n地址：{self.url}\n状态码：{resp_status_code}\n故障类型：{fault_type}\n提示：{hint}",
                    fault_type=fault_type,
                    error_msg=None,
                    status_code=resp_status_code,
                )
                self.callback_status(
                    f"[异常] 状态码：{resp_status_code}，故障类型：{fault_type}"
                )

        self.sleep_with_interrupt(self.interval_err)

    def analyze_status_code(self, code):
        hint = "未知错误"
        if 400 <= code < 500:
            fault = f"客户端错误({code})"
            hints = {
                400: "请求参数格式错误，请检查请求内容",
                401: "需要身份验证，请检查登录状态或访问令牌",
                403: "服务器拒绝访问，请检查权限或IP是否被阻止",
                404: "请检查URL是否正确或页面是否已删除",
                405: "请求使用的HTTP方法不被服务器允许",
                406: "服务器无法提供请求头中指定的格式",
                408: "服务器等待请求超时，请检查网络连接",
                409: "请求与资源当前状态冲突",
                410: "请求的资源已被永久删除，无法恢复",
                413: "请求体大小超过服务器限制",
                414: "请求的URL长度超过服务器允许的限制",
                415: "请求的媒体类型不被服务器支持",
                421: "请求被发送到无法处理的服务器",
                422: "请求参数格式正确但内容验证失败",
                429: "已超出请求限制，请稍后再试",
                431: "请求头字段大小超过服务器限制",
            }
            hint = hints.get(code, hint)
        elif 500 <= code < 600:
            fault = f"服务器错误({code})"
            hints = {
                500: "服务器遇到意外错误，请联系管理员",
                501: "服务器不支持请求的功能或方法",
                502: "服务器作为网关收到无效响应",
                503: "服务器暂时无法处理请求，请稍后再试",
                504: "服务器作为网关未能及时收到响应",
                505: "服务器不支持请求使用的HTTP版本",
                506: "服务器内部配置错误导致协商失败",
                511: "需要进行网络认证才能访问",
            }
            hint = hints.get(code, hint)
        else:
            fault = f"未知状态码({code})"
            hint = "遇到未知状态码，请检查服务器配置"

        return fault, hint

    def report_ok(self, code):
        msg = f"提示：网站正常运行中\n地址：{self.url}\n状态码：{code}\n系统状态：正常"
        self.send_dingding(msg, title="系统提醒", status_code=code)
        self.callback_status(f"[正常] 状态码：{code}，系统状态：正常")

    def send_dingding(
        self,
        message,
        title="网站报警",
        fault_type=None,
        error_msg=None,
        status_code=None,
    ):
        webhook = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}"
        headers = {"Content-Type": "application/json"}

        # 组装消息内容，包含额外字段，方便查看
        content = f"【{title}】\n{message}"
        if status_code is not None:
            content += f"\n状态码：{status_code}"
        if fault_type is not None:
            content += f"\n故障类型：{fault_type}"
        if error_msg is not None:
            content += f"\n异常信息：{error_msg}"

        data = {"msgtype": "text", "text": {"content": content}}

        try:
            requests.post(webhook, headers=headers, data=json.dumps(data))
        except Exception as e:
            print(f"[推送失败] {e}")

    def handle_exception(self, fault_type, error_msg):
        # 异常处理，推送包含异常信息的消息
        msg = f"报警：{fault_type}\n地址：{self.url}\n异常信息：{error_msg}"
        self.send_dingding(msg, fault_type=fault_type, error_msg=error_msg)
        self.callback_status(f"[异常] {fault_type}：{error_msg}")

    def sleep_with_interrupt(self, seconds):
        for _ in range(seconds):
            if self.stop_event.is_set():
                break
            time.sleep(1)
