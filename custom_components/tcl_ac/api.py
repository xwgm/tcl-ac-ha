"""TCL IoT API 客户端（账号级，支持多设备）。

职责：token 管理、登录、设备列表枚举、状态查询、控制下发。
所有网络请求走 stdlib urllib，无第三方依赖。
"""
import json
import logging
import random
import ssl
import time
import uuid
import urllib.request

from .const import (
    CONFIG_FILE,
    APP_ID, APP_TENANT_ID, APP_SECRET,
    IOS_APP_ID, IOS_APP_SECRET, IOS_TENANT_ID, IOS_APP_VERSION,
    IOS_PLATFORM_TYPE, IOS_STORE_UUID, IOS_USER_AGENT, IOS_REPORT_STATE,
    LOGIN_API,
    IOT_HOST, DEVICE_STATUS_API, CONTROL_DEVICE_API, CONTROL_SOURCE, PLATFORM_TYPE, USER_AGENT,
    GET_DEVICES_API,
)
from . import crypto

_LOGGER = logging.getLogger(__name__)


class TclApi:
    """账号级 TCL API 客户端。"""

    def __init__(self):
        self._token = ""
        self._token_ts = 0.0
        self._account_id = ""
        self._username = ""
        self._password = ""

    # ──────────────── Token 管理 ────────────────

    def _load_config(self) -> dict:
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self, cfg: dict) -> None:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    def get_token(self) -> str:
        """获取有效 token（缓存 3000 秒）。"""
        if self._token and (time.time() - self._token_ts) < 3000:
            return self._token
        cfg = self._load_config()
        # 1) 先用 refreshToken 续期
        try:
            url = (
                f"https://cn.account.tcl.com/auth/auth/refershToken"
                f"?appId={APP_ID}&accountId={cfg.get('account_id', '')}"
                f"&tenantId={APP_TENANT_ID}&appSecret={APP_SECRET}"
            )
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
            result = self._http(url, headers)
            self._token = result["accessToken"]
            self._token_ts = time.time()
            cfg["access_token"] = self._token
            cfg["refresh_token"] = result["refreshToken"]
            cfg["access_token_ts"] = self._token_ts
            self._save_config(cfg)
            _LOGGER.debug("tcl_ac: token 刷新成功")
            return self._token
        except Exception as err:
            # 2) refresh 失败且有账号密码 → 自动登录获取新 token
            if self._username and self._password:
                _LOGGER.warning(
                    "tcl_ac: refreshToken 失效（%s），尝试用账号密码重新登录", err
                )
                return self.login_by_password(self._username, self._password)
            # 3) 无账号密码 → 明确告警
            _LOGGER.error(
                "tcl_ac: token 已过期且未配置账号密码，请在集成设置中重新配置"
            )
            raise

    def login_by_password(self, username: str, password: str) -> str:
        """账号密码登录：RSA 加密参数 → 登录 → 写回 token 文件。"""
        device_id = str(uuid.uuid4()).upper()
        params = {
            "deviceId": device_id,
            "password": crypto.md5_hash(password),
            "channel": IOS_STORE_UUID,
            "tenantId": IOS_TENANT_ID,
            "appSecret": IOS_APP_SECRET,
            "username": username,
            "appId": IOS_APP_ID,
            "reportState": IOS_REPORT_STATE,
        }
        url = f"{LOGIN_API}?{crypto.encrypt_url_params(params)}"
        body = crypto.encrypt_body(params)
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "t-platform-type": IOS_PLATFORM_TYPE,
            "uid": "",
            "Accept": "*/*",
            "cid": str(uuid.uuid4()).upper(),
            "Accept-Language": "zh-Hans-CN;q=1, zh-Hant-CN;q=0.9, en-CN;q=0.8",
            "token": "",
            "EncryptVersion": "2.0",
            "t-app-version": IOS_APP_VERSION,
            "t-store-uuid": IOS_STORE_UUID,
            "Encrypt": "true",
            "User-Agent": IOS_USER_AGENT,
            "t-application-name": "",
        }
        result = self._http(url, headers, data=body, method="POST")
        if "accessToken" not in result:
            raise RuntimeError(f"TCL 密码登录失败: {result.get('message', result)}")
        self._token = result["accessToken"]
        self._token_ts = time.time()
        self._account_id = result["accountId"]
        self._username = username
        self._password = password
        cfg = self._load_config()
        cfg["account_id"] = result["accountId"]
        cfg["access_token"] = self._token
        cfg["refresh_token"] = result["refreshToken"]
        cfg["access_token_ts"] = self._token_ts
        self._save_config(cfg)
        _LOGGER.info("tcl_ac: 账号密码登录成功，已更新 token")
        return self._token

    # ──────────────── 设备列表枚举 ────────────────

    def list_devices(self) -> list[dict]:
        """拉取账号下全量设备列表。返回设备字典列表，每项含：
        deviceId, nickName, category, productKey, isOnline, weChatControl
        """
        headers = {
            "Host": IOT_HOST,
            "accessToken": self.get_token(),
            "t-app-version": "2.7.33",
            "t-store-uuid": "TCL+",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json;charset=UTF-8",
            "t-platform-type": PLATFORM_TYPE,
        }
        result = self._http(GET_DEVICES_API, headers)
        devices = result.get("data", [])
        _LOGGER.info("tcl_ac: 枚举到 %d 台设备", len(devices))
        for d in devices:
            _LOGGER.debug(
                "  设备: id=%s name=%s category=%s online=%s wxCtrl=%s",
                d.get("deviceId"), d.get("nickName"), d.get("category"),
                d.get("isOnline"), d.get("weChatControl"),
            )
        return devices

    # ──────────────── 设备状态 & 控制（通用） ────────────────

    def _iot_headers(self) -> dict:
        return {
            "Host": IOT_HOST,
            "accessToken": self.get_token(),
            "t-app-version": "2.7.33",
            "t-store-uuid": "TCL+",
            "Content-Type": "application/json;charset=UTF-8",
            "t-platform-type": PLATFORM_TYPE,
            "User-Agent": USER_AGENT,
        }

    def get_status(self, device_id: str) -> dict:
        """查询单台设备状态。返回 status 字典。"""
        return self._http(
            DEVICE_STATUS_API,
            self._iot_headers(),
            data={"deviceId": device_id},
            method="POST",
        ).get("data", {}).get("status", {})

    def send_control(self, device_id: str, attrs: dict) -> bool:
        """向单台设备发送控制指令。返回是否成功。"""
        url = CONTROL_DEVICE_API.format(device_id=device_id)
        body = {
            "msgId": f"ha_{int(random.random() * 1e5)}_{int(time.time() * 1000)}",
            "source": CONTROL_SOURCE,
            "version": "3.0.0",
            "params": [{k: v} for k, v in attrs.items()],
        }
        result = self._http(url, self._iot_headers(), data=body, method="POST")
        return result.get("code") == "200"

    # ──────────────── 底层 HTTP ────────────────

    def _http(self, url: str, headers: dict, data=None, method: str = "GET"):
        if isinstance(data, (bytes, bytearray)):
            body = bytes(data)
        elif data is not None:
            body = json.dumps(data).encode()
        else:
            body = None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return json.loads(resp.read().decode())
