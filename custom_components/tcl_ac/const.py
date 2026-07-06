DOMAIN = "tcl_ac"

CONFIG_FILE = "/config/tcl_token.json"
# 留空即可；device_id 请在 configuration.yaml 的 tcl_ac: 段填写，
# 这样 HACS 更新组件时不会覆盖你的配置。
DEVICE_ID = ""

# TCL 微信小程序公共凭据（所有用户通用，用于刷新 token）
APP_ID = "55141607047147220"
APP_TENANT_ID = "tcl"
APP_SECRET = "48980a392dc2078cbda5b3035a084a7bcee34a69cace18baa715e61d790b01d4"

# ===== 针对"仅支持 TCL App 控制"设备的改造 =====
# 原版写死 source="miniprogram"（小程序）。你的空调设备级限制为"仅 App 控制"，
# 故把控制请求的 source 伪装成 app，并改用 App 的 UA / 平台标识，绕过限制。
# 若控制失败：① 试把 CONTROL_SOURCE 改成 "TCL+"；② 用手机抓 TCL 智家 App 真实流量确认实际值。
CONTROL_SOURCE = "app"
PLATFORM_TYPE = "iOS"
USER_AGENT = "TCLPlus/2.6.1"

MODE_MAP = {"auto": 0, "cool": 1, "dry": 2, "fan": 3, "heat": 4}
MODE_REVERSE = {0: "auto", 1: "cool", 2: "dry", 3: "fan_only", 4: "heat"}

FAN_MAP = {"auto": 0, "low": 20, "medium": 50, "high": 75, "full": 100}
