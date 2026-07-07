DOMAIN = "tcl_ac"

CONFIG_FILE = "/config/tcl_token.json"

# 账号密码（可选）：填写后启用 token 自动刷新
# 都不填 = 纯 refreshToken 模式（refreshToken 过期需手动重抓）；
# 都填上 = refreshToken 失效时自动用账号密码换新 token，永久免维护。
USERNAME = ""   # TCL 账号（手机号）
PASSWORD = ""   # TCL 密码（明文，仅存于本地 configuration.yaml）

# 公共凭据（用于获取/刷新 token）
APP_ID = "55141607047147220"
APP_TENANT_ID = "tcl"
APP_SECRET = "48980a392dc2078cbda5b3035a084a7bcee34a69cace18baa715e61d790b01d4"

# 账号密码登录所需凭据
# 与上方 token 刷新凭据相互独立
IOS_APP_ID = "28411606743791229"
IOS_APP_SECRET = "8f2538acdb620574bf334cd35114f7178c8e790bf216edb7ba749bd6f6d86b44"
IOS_TENANT_ID = "TCLPLUS"
IOS_APP_VERSION = "2.6.1(1344)"
IOS_PLATFORM_TYPE = "iOS"
IOS_STORE_UUID = "TCL+"
IOS_USER_AGENT = "TCLPlus/2.6.1 (iPhone; iOS 15.4.1; Scale/3.00)"
IOS_REPORT_STATE = '{"os":"iOS","osVersion":"15.4.1","appVersion":"2.6.1","deviceModel":"iPhone"}'  # noqa: E501
# 账号密码登录接口（参数需 RSA 加密，见 crypto.py）
LOGIN_API = "https://cn.account.tcl.com/auth/auth/login"

# IoT API 端点
IOT_HOST = "io.zx.tcljd.com"
DEVICE_STATUS_API = f"https://{IOT_HOST}/v1/thing/status"
CONTROL_DEVICE_API = f"https://{IOT_HOST}/v1/control/property/{{device_id}}"
GET_DEVICES_API = f"https://{IOT_HOST}/v1/tclplus/weChat/user/user_devices"

# 控制请求标识
CONTROL_SOURCE = "app"
PLATFORM_TYPE = "iOS"
USER_AGENT = "TCLPlus/2.6.1"

# 设备类型（对应 API 返回的 category 字段，已通过 SSH 实际验证）
CATEGORY_AC = "AC"           # 空调（API 返回大写 "AC"）
CATEGORY_FRIDGE = "RF"       # 冰箱（API 返回 "RF"）
CATEGORY_UNKNOWN = "unknown"

# 空调模式映射
MODE_MAP = {"auto": 0, "cool": 1, "dry": 2, "fan": 3, "heat": 4}
MODE_REVERSE = {0: "auto", 1: "cool", 2: "dry", 3: "fan_only", 4: "heat"}

FAN_MAP = {"auto": 0, "low": 20, "medium": 50, "high": 75, "full": 100}

# 空调预设模式
PRESET_MODES = ["none", "eco", "sleep", "health"]
PRESET_MODE_LABELS = {
    "none": "普通",
    "eco": "节能",
    "sleep": "睡眠",
    "health": "健康",
}

# 冰箱模式
FRIDGE_MODES = ["ai", "quick_cool", "quick_freeze"]
FRIDGE_MODE_LABELS = {
    "ai": "AI智能",
    "quick_cool": "速冷",
    "quick_freeze": "速冻",
}
FRIDGE_MODE_VALUES = {  # API 值
    "ai": 0,
    "quick_cool": 1,
    "quick_freeze": 2,
}

# 冰箱温度范围（根据 App 截图）
FRIDGE_FRIDGE_TEMP_MIN = 2     # 冷藏室最低
FRIDGE_FRIDGE_TEMP_MAX = 8     # 冷藏室最高
FRIDGE_FREEZER_TEMP_MIN = -24  # 冷冻室最低
FRIDGE_FREEZER_TEMP_MAX = -15  # 冷冻室最高

SCAN_INTERVAL_SECONDS = 30
