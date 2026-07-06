"""
TCL 微信小程序 Token 抓包工具
用法：
  1. 运行本脚本（会启动代理服务器 127.0.0.1:8888）
  2. 设置系统代理或微信代理指向 127.0.0.1:8888
  3. 首次运行需安装 mitmproxy CA 证书（脚本会自动提示）
  4. 打开微信 TCL 小程序，登录/刷新一下
  5. 脚本会自动捕获并显示 account_id 和 refreshToken
"""

import json
import sys
import os
import subprocess

from mitmproxy import http, ctx

class TclTokenGrabber:
    def __init__(self):
        self.account_id = None
        self.refresh_token = None
        self.access_token = None
        self.found = False

    def response(self, flow: http.HTTPFlow):
        """拦截响应，提取 token"""
        url = flow.request.pretty_url

        # 拦截所有 cn.account.tcl.com 响应，提取 token
        if "cn.account.tcl.com" in url:
            try:
                data = json.loads(flow.response.content)
                ctx.log.info(f"[TCL] 响应 {url[:80]}: {json.dumps(data, ensure_ascii=False)[:200]}")

                # 从任何响应中提取 accessToken/refreshToken
                if isinstance(data, dict):
                    if data.get("accessToken"):
                        self.access_token = data["accessToken"]
                        ctx.log.info(f"[TCL] 捕获 accessToken")
                    if data.get("refreshToken"):
                        self.refresh_token = data["refreshToken"]
                        ctx.log.info(f"[TCL] 捕获 refreshToken")
                    if data.get("accountId"):
                        self.account_id = str(data["accountId"])
                    # 从 URL 提取 accountId
                    if "accountId=" in url and "?" in url:
                        for param in url.split("?")[1].split("&"):
                            if param.startswith("accountId="):
                                self.account_id = param.split("=")[1]

                    if self.account_id and self.refresh_token and not self.found:
                        self._print_result("login 响应")
            except Exception:
                pass

        # 拦截 getUserInfoByToken 接口
        if "cn.account.tcl.com/user/user/getUserInfoByToken" in url:
            try:
                data = json.loads(flow.response.content)
                if "data" in data and "accountId" in data.get("data", {}):
                    self.account_id = data["data"]["accountId"]
                    ctx.log.info(f"[TCL] 从用户信息接口获取 accountId: {self.account_id}")
            except Exception as e:
                ctx.log.error(f"解析用户信息响应失败: {e}")

    def request(self, flow: http.HTTPFlow):
        """拦截请求，提取 header 中的 token"""
        url = flow.request.pretty_url

        # 任何发往 TCL 服务器的请求都可能包含 token
        if "cn.account.tcl.com" in url or "io.zx.tcljd.com" in url:
            headers = flow.request.headers

            # 从 header 中提取 refreshToken
            if "refreshToken" in headers and headers["refreshToken"]:
                self.refresh_token = headers["refreshToken"]
                ctx.log.info(f"[TCL] 从请求 header 捕获 refreshToken")

            # 从 header 中提取 accessToken
            if "accessToken" in headers and headers["accessToken"]:
                self.access_token = headers["accessToken"]

            if "TCL-Authorization" in headers and headers["TCL-Authorization"]:
                self.access_token = headers["TCL-Authorization"]

            # 从 URL 提取 accountId
            if "accountId=" in url:
                for param in url.split("?")[1].split("&"):
                    if param.startswith("accountId="):
                        self.account_id = param.split("=")[1]
                        ctx.log.info(f"[TCL] 从 URL 捕获 accountId: {self.account_id}")

            # 每次有新信息都尝试输出
            if self.account_id and self.refresh_token and not self.found:
                self._print_result("请求拦截")

    def _print_result(self, source: str):
        self.found = True
        result = {
            "account_id": self.account_id,
            "refresh_token": self.refresh_token,
        }
        # 保存到文件
        output_path = os.path.join(os.path.dirname(__file__), "tcl_token.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        print("  TCL Token 抓取成功！")
        print("=" * 60)
        print(f"  来源: {source}")
        print(f"  account_id:    {self.account_id}")
        print(f"  refreshToken:  {self.refresh_token[:20]}...{self.refresh_token[-10:]}")
        if self.access_token:
            print(f"  accessToken:   {self.access_token[:20]}...{self.access_token[-10:]}")
        print(f"\n  已保存到: {output_path}")
        print("=" * 60)
        print("  现在可以关闭本脚本，将上面的值填入 Home Assistant")
        print("=" * 60 + "\n")

addons = [TclTokenGrabber()]

if __name__ == "__main__":
    # 直接启动 mitmproxy
    cert_dir = os.path.expanduser("~/.mitmproxy")
    cert_file = os.path.join(cert_dir, "mitmproxy-ca-cert.cer")

    print("=" * 60)
    print("  TCL Token 抓包工具")
    print("=" * 60)
    print()
    print("  正在启动代理服务器 127.0.0.1:8888 ...")
    print()

    # 用 mitmdump 启动，加载自身作为 addon
    mitmdump = os.path.join(os.path.dirname(sys.executable), "mitmdump")
    if os.name == "nt":
        mitmdump += ".exe"

    # 先生成证书（如果不存在）
    if not os.path.exists(cert_file):
        print("  首次运行，正在生成 CA 证书...")
        proc = subprocess.Popen(
            [mitmdump, "--listen-port", "18888", "--set", "connection_strategy=lazy"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        import time
        time.sleep(2)
        proc.terminate()
        proc.wait()

    if os.path.exists(cert_file):
        print(f"  CA 证书位置: {cert_file}")
        print()
        print("  [重要] 请先安装 CA 证书：")
        print(f"    1. 双击打开 {cert_file}")
        print("    2. 选择 '安装证书' → '当前用户' → '将所有证书放入下列存储'")
        print("    3. 浏览 → 选择 '受信任的根证书颁发机构' → 确定")
        print()

    print("  证书安装后，设置代理：")
    print("    Windows 设置 → 网络和 Internet → 代理 → 手动设置代理")
    print("    地址: 127.0.0.1  端口: 8888")
    print()
    print("  然后打开 微信电脑版 → TCL 小程序 → 登录/操作一下")
    print("  本工具会自动捕获 token")
    print("=" * 60)
    print()

    subprocess.run([
        mitmdump,
        "--listen-port", "8888",
        # 如果你用了代理软件（如 Clash），取消下面这行的注释，端口改成你的代理端口
        # "--mode", "upstream:http://127.0.0.1:7897",
        "--set", "connection_strategy=lazy",
        "-s", __file__,
    ])
