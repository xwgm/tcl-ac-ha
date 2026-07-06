#!/usr/bin/env python3
"""
列出 TCL 账号下的设备，找出空调的 deviceId。
依赖：同目录下的 tcl_token.json（由 grab_token.py 生成，含 account_id + refresh_token）

用法：
  pip install requests
  python verify_token.py
"""
import json
import ssl
import time
import os
import urllib.request

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tcl_token.json")
APP_ID = "55141607047147220"
APP_TENANT_ID = "tcl"
APP_SECRET = "48980a392dc2078cbda5b3035a084a7bcee34a69cace18baa715e61d790b01d4"

def get_token():
    cfg = json.load(open(CONFIG_FILE))
    if cfg.get("access_token") and (time.time() - cfg.get("access_token_ts", 0)) < 3000:
        return cfg["access_token"]
    url = (f"https://cn.account.tcl.com/auth/auth/refershToken"
           f"?appId={APP_ID}&accountId={cfg.get('account_id','')}"
           f"&tenantId={APP_TENANT_ID}&appSecret={APP_SECRET}")
    headers = {
        "Host": "cn.account.tcl.com",
        "Content-Type": "application/json;charset=UTF-8",
        "t-platform-type": "iOS",
        "Encrypt": "false",
        "EncryptVersion": "2.0",
        "t-app-version": "2.7.33",
        "t-store-uuid": "TCL+",
        "User-Agent": "TCLPlus/2.6.1",
        "refreshToken": cfg.get("refresh_token", ""),
    }
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        data = json.loads(r.read().decode())
    cfg["access_token"] = data["accessToken"]
    cfg["refresh_token"] = data["refreshToken"]
    cfg["access_token_ts"] = time.time()
    json.dump(cfg, open(CONFIG_FILE, "w"), indent=2, ensure_ascii=False)
    return data["accessToken"]

def list_devices():
    token = get_token()
    url = "https://io.zx.tcljd.com/v1/tclplus/weChat/user/user_devices"
    headers = {
        "Host": "io.zx.tcljd.com",
        "accessToken": token,
        "t-app-version": "2.7.33",
        "t-store-uuid": "TCL+",
        "Content-Type": "application/json;charset=UTF-8",
        "t-platform-type": "iOS",
        "User-Agent": "TCLPlus/2.6.1",
    }
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        data = json.loads(r.read().decode())

    print("=== 原始响应 ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    devices = data.get("data", {})
    if isinstance(devices, dict):
        devices = devices.get("devices", [])
    print("\n=== 设备列表 ===")
    for d in devices:
        print(f"名称:{d.get('name')}  设备Id:{d.get('deviceId')}  在线:{d.get('online')}  productKey:{d.get('productKey')}")
    print("\n把空调对应的 deviceId 填到 HA 的 configuration.yaml 的 tcl_ac: 段（device_id: \"...\")")

if __name__ == "__main__":
    list_devices()
