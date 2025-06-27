import time
import json
import requests
import ssl
import socket
from urllib.parse import urlparse, urljoin
from datetime import datetime
from ssl_checker import check_ssl_status  # 你之前的模块


class Monitor:

    def __init__(
        self,
        url,
        token,
        interval_ok,
        interval_err,
        callback_status,
        stop_event,
        callback_push_status,  # ✅ 新增参数
    ):
        self.url = url
        self.token = token
        self.interval_ok = interval_ok
        self.interval_err = interval_err
        self.callback_status = callback_status
        self.stop_event = stop_event
        self.timeout = 30  # 请求超时秒数，可调整
        self.callback_push_status = callback_push_status  # ✅ 保存回调函数

    def start(self, immediate=True):
        if not immediate:
            self.sleep_with_interrupt(self.interval_ok)

        while not self.stop_event.is_set():
            try:
                self.check_website()
            except Exception as e:
                self.handle_exception("未知异常", str(e))
                self.sleep_with_interrupt(self.interval_err)

    def check_website(self):
        input_domain = urlparse(self.url).netloc
        paths_to_check = [""]

        resp_status_code = None
        resp_domain = input_domain
        error_msg = None

        for path in paths_to_check:
            full_url = urljoin(self.url, path)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": self.url,  # 有时Referer也能帮忙
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }

            # 默认尝试正常验证证书
            try:
                path_resp = requests.get(
                    full_url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    headers=headers,
                )
                resp_status_code = path_resp.status_code
                resp_domain = urlparse(path_resp.url).netloc
            except requests.exceptions.SSLError as ssl_err:
                # 证书错误，尝试忽略证书验证再请求
                if (
                    "certificate verify failed" in str(ssl_err).lower()
                    or "self signed certificate" in str(ssl_err).lower()
                ):
                    try:
                        path_resp = requests.get(
                            full_url,
                            timeout=self.timeout,
                            allow_redirects=True,
                            headers=headers,
                            verify=False,
                        )
                        resp_status_code = path_resp.status_code
                        resp_domain = urlparse(path_resp.url).netloc
                        error_msg = (
                            f"证书验证失败，使用不验证模式访问成功，原始错误：{ssl_err}"
                        )
                    except Exception as e2:
                        error_msg = f"忽略证书访问失败：{e2}"
                else:
                    error_msg = str(ssl_err)
            except requests.RequestException as e:
                error_msg = str(e)

            # 检测结果处理
            if resp_status_code == 200 and resp_domain == input_domain:
                cert_info = (
                    check_ssl_status(self.url) if self.url.startswith("https") else None
                )

                # 证书无效但网站正常访问，提示证书异常但不算故障
                if cert_info and cert_info.get("status") != "valid":
                    # 证书异常但状态200正常
                    cert_status = cert_info.get("status")
                    detail = ""
                    if cert_status == "expired":
                        detail = f"证书已过期，到期时间：{cert_info.get('not_after')}"
                    elif cert_status == "not_yet_valid":
                        detail = (
                            f"证书尚未生效，生效时间：{cert_info.get('not_before')}"
                        )
                    elif cert_status == "hostname_mismatch":
                        detail = f"证书主机名不匹配，期望：{cert_info.get('expected')}, 证书包含：{cert_info.get('cert_hosts')}"
                    elif cert_status == "self_signed":
                        detail = "证书为自签名证书"
                    elif cert_status == "ssl_error":
                        detail = f"SSL错误：{cert_info.get('error')}"
                    else:
                        detail = f"证书状态异常：{cert_status}"

                    self.report_ok(
                        resp_status_code, cert_info=cert_info, cert_warn=detail
                    )
                    self.sleep_with_interrupt(self.interval_ok)
                    return

                # 证书有效或非HTTPS
                self.report_ok(resp_status_code, cert_info)
                self.sleep_with_interrupt(self.interval_ok)
                return

            break  # 如果访问失败或非200，跳出循环

        # 处理失败或异常情况
        if resp_status_code is not None:
            if resp_domain != input_domain:
                fault_type = "根地址跳转到其他域名"
                self.send_dingding(
                    title="网站报警",
                    address=self.url,
                    system_status="故障",
                    system_hint=fault_type + f"，跳转后域名：{resp_domain}",
                    status_code=resp_status_code,
                    warm_tip="疑似域名拦截！请检查服务器或云平台流量套餐等状态!",
                )
                self.callback_status(f"[异常] {fault_type}，状态码：{resp_status_code}")
            else:
                fault_type, hint = self.analyze_status_code(resp_status_code)
                self.send_dingding(
                    title="网站报警",
                    address=self.url,
                    system_status="故障",
                    system_hint=hint,
                    status_code=resp_status_code,
                    exception_info=(
                        error_msg if fault_type.startswith("未知状态码") else None
                    ),
                )
                self.callback_status(
                    f"[异常] 状态码：{resp_status_code}，故障类型：{fault_type}"
                )
        else:
            fault_type = "无响应状态码"
            hint = "可能DNS解析失败|请求超时|网络故障等无响应错误！"
            self.send_dingding(
                title="请求异常",
                address=self.url,
                system_status="故障",
                system_hint=hint,
                exception_info=error_msg,
            )
            self.callback_status(f"[异常] {fault_type}：{error_msg}")

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

    def report_ok(self, code, cert_info=None, cert_warn=None):
        # 获取IP地理位置信息
        location = self.get_ip_location()

        location_str = f"{location.get('country')} {location.get('region')} {location.get('city')}" if not location.get('error') else f"获取地理位置失败: {location.get('error')}"
        print("用户地区：{location_str}")
        lines = [
            f"提示：网站正常运行中",
            f"地址：{self.url}",
            f"状态码：{code}",
            f"系统状态：正常",
            f"用户地区:{location_str}",
        ]
        if cert_info and cert_info.get("status") == "valid":
            lines.append(f"证书有效期至：{cert_info.get('not_after')}")
        elif cert_warn:
            lines.append(f"证书异常提示：{cert_warn}")

        # 将地区信息添加到推送内容中
        location_content = location_str
        self.send_dingding(
            title="系统提醒",
            address=self.url,
            system_status="正常",
            system_hint="网站响应正常",
            status_code=code,
            location_content=location_content,
            warm_tip=(
                lines[-1]
                if cert_warn or (cert_info and cert_info.get("status") == "valid")
                else None
            ),
        )
        self.callback_status(f"[正常] 状态码：{code}，系统状态：正常")

    def send_dingding(
        self,
        message=None,
        title="网站报警",
        address=None,
        system_status=None,
        system_hint=None,
        status_code=None,
        exception_info=None,
        warm_tip=None,
        location_content=None,
    ):
        content_lines = []
        if message:
            content_lines.append(message)
        else:
            if title:
                content_lines.append(f"【{title}】")
            if system_hint:
                content_lines.append(system_hint)
            if address:
                content_lines.append(f"地址：{address}")
            if system_status:
                content_lines.append(f"系统状态：{system_status}")
            if status_code is not None:
                content_lines.append(f"状态码：{status_code}")
            if warm_tip:
                content_lines.append(f"温馨提示：{warm_tip}")
            if exception_info:
                content_lines.append(f"异常信息：{exception_info}")
            if  location_content:
                content_lines.append(f"用户地区：{location_content}")    

        content = "\n".join(content_lines)

        webhook = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}"
        headers = {"Content-Type": "application/json"}
        data = {"msgtype": "text", "text": {"content": content}}
        # ✅ 显示“正在推送”
        if self.callback_push_status:
            self.callback_push_status("正在推送告警到钉钉...")
        try:
            resp=requests.post(webhook, headers=headers, data=json.dumps(data))
            if resp.status_code == 200:
                # ✅ 推送成功
                if self.callback_push_status:
                    self.callback_push_status("✅ 推送成功")
            else:
                # ✅ 推送失败（钉钉返回非 200）
                if self.callback_push_status:
                    self.callback_push_status(
                        f"❌ 推送失败，状态码：{resp.status_code}"
                    )
        except Exception as e:
            # ✅ 推送异常
            if self.callback_push_status:
                self.callback_push_status(f"❌ 推送异常：{e}")
            print(f"[推送失败] {e}")

    def handle_exception(self, fault_type, error_msg):
        msg = f"报警：{fault_type}\n地址：{self.url}\n异常信息：{error_msg}"
        self.send_dingding(message=msg)
        self.callback_status(f"[异常] {fault_type}：{error_msg}")

    def get_ip_location(self):
        try:
            response = requests.get('https://ipinfo.io/json')
            data = response.json()
            return {
                'ip': data.get('ip'),
                'country': data.get('country'),
                'region': data.get('region'),
                'city': data.get('city')
            }
        except Exception as e:
            return {'error': f'获取IP地理位置失败: {str(e)}'}

    def sleep_with_interrupt(self, seconds):
        for _ in range(seconds):
            if self.stop_event.is_set():
                break
            time.sleep(1)
