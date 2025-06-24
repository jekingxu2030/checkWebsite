# # =====================
# # ssl_checker.py
# import ssl
# import socket
# from urllib.parse import urlparse
# from datetime import datetime
# import requests


# def check_ssl_status(url):
#     try:
#         hostname = urlparse(url).hostname
#         context = ssl.create_default_context()
#         with socket.create_connection((hostname, 443), timeout=5) as sock:
#             with context.wrap_socket(sock, server_hostname=hostname) as ssock:
#                 cert = ssock.getpeercert()
#                 not_after = cert.get("notAfter")
#                 not_before = cert.get("notBefore")
#                 subject = cert.get("subject", [])
#                 issuer = cert.get("issuer", [])
#                 san_list = cert.get("subjectAltName", [])

#                 now = datetime.utcnow()
#                 expire_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
#                 start_date = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")

#                 # 检查有效期
#                 if expire_date < now:
#                     return {
#                         "status": "expired",
#                         "not_after": expire_date.strftime("%Y-%m-%d"),
#                     }
#                 elif start_date > now:
#                     return {
#                         "status": "not_yet_valid",
#                         "not_before": start_date.strftime("%Y-%m-%d"),
#                     }

#                 # 检查主机名是否匹配
#                 hostnames = [x[1] for x in san_list if x[0] == "DNS"]
#                 if hostname not in hostnames:
#                     return {
#                         "status": "hostname_mismatch",
#                         "expected": hostname,
#                         "cert_hosts": hostnames,
#                     }

#                 # 判断是否自签名
#                 if subject == issuer:
#                     return {"status": "self_signed"}

#                 # 进一步检测证书是否被系统信任（模拟浏览器行为）
#                 trusted, error = is_browser_trusted(url)
#                 if not trusted:
#                     return {"status": "untrusted_by_system", "error": error}

#                 return {
#                     "status": "valid",
#                     "not_after": expire_date.strftime("%Y-%m-%d"),
#                 }

#     except ssl.SSLError as e:
#         return {"status": "ssl_error", "error": str(e)}
#     except socket.timeout:
#         return {"status": "timeout"}
#     except Exception as e:
#         return {"status": "unknown_error", "error": str(e)}


# def is_browser_trusted(url):
#     try:
#         resp = requests.get(url, timeout=5)
#         # 访问成功且无SSL错误，说明被系统信任
#         return True, None
#     except requests.exceptions.SSLError as e:
#         # SSL错误通常表示证书不被信任或验证失败
#         return False, str(e)
#     except Exception as e:
#         return False, str(e)


# ====================
import ssl
import socket
from urllib.parse import urlparse
from datetime import datetime
import requests
from ssl import CertificateError, match_hostname


def check_ssl_status(url, timeout=5):
    try:
        hostname = urlparse(url).hostname
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                not_after = cert.get("notAfter")
                not_before = cert.get("notBefore")

                now = datetime.utcnow()
                try:
                    expire_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    start_date = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")
                except Exception as e:
                    return {"status": "parse_date_error", "error": str(e)}

                # 检查有效期
                if expire_date < now:
                    return {
                        "status": "expired",
                        "not_after": expire_date.strftime("%Y-%m-%d"),
                    }
                if start_date > now:
                    return {
                        "status": "not_yet_valid",
                        "not_before": start_date.strftime("%Y-%m-%d"),
                    }

                # 使用系统方法验证主机名（包括通配符）
                try:
                    match_hostname(cert, hostname)
                except CertificateError as e:
                    return {"status": "hostname_mismatch", "error": str(e)}

                # 判断是否自签名（subject和issuer完全相等）
                subject = cert.get("subject", [])
                issuer = cert.get("issuer", [])
                if subject == issuer:
                    return {"status": "self_signed"}

                # 进一步检测证书是否被系统信任（模拟浏览器行为）
                trusted, error = is_browser_trusted(url, timeout)
                if not trusted:
                    return {"status": "untrusted_by_system", "error": error}

                return {
                    "status": "valid",
                    "not_after": expire_date.strftime("%Y-%m-%d"),
                }

    except ssl.SSLError as e:
        return {"status": "ssl_error", "error": str(e)}
    except socket.timeout:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "unknown_error", "error": str(e)}


def is_browser_trusted(url, timeout=5):
    try:
        resp = requests.get(url, timeout=timeout, verify=True)
        resp.close()
        return True, None
    except requests.exceptions.SSLError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)
