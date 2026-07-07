"""TCL AC v2.0：账号级多设备集成入口。

流程：手机号+密码登录 → 枚举全量设备 → 按设备类型分发创建实体。
"""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CATEGORY_AC,
    CATEGORY_FRIDGE,
    SCAN_INTERVAL_SECONDS,
)
from .api import TclApi

_LOGGER = logging.getLogger(__name__)

# 支持的平台
PLATFORMS = [
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.LOCK,
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML 配置方式（v2.0 不再支持，统一走 config_flow UI）。"""
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """UI 添加集成时的入口。登录 → 枚举 → 建实体。"""
    data = entry.data or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if not (username and password):
        _LOGGER.error("tcl_ac: 缺少用户名或密码，请在集成设置中重新配置")
        return False

    # 1) 登录获取 token
    api = TclApi()
    try:
        token = await hass.async_add_executor_job(
            api.login_by_password, username, password
        )
    except Exception as err:
        _LOGGER.error("tcl_ac: 登录失败: %s", err)
        return False

    # 2) 枚举账号下所有设备
    try:
        devices = await hass.async_add_executor_job(api.list_devices)
    except Exception as err:
        _LOGGER.error("tcl_ac: 设备列表枚举失败: %s", err)
        return False

    if not devices:
        _LOGGER.warning("tcl_ac: 账号下未发现任何设备")
        return True

    # 3) 按 device 类型分组，存入 hass.data 供各平台使用
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["api"] = api
    hass.data[DOMAIN]["devices"] = devices

    # 4) 注册各平台（各平台从 hass.data 取设备信息自行建实体）
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    _LOGGER.info("tcl_ac v2.0 初始化完成：%d 台设备", len(devices))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载集成。"""
    unload_ok = all(
        await hass.config_entries.async_forward_entry_unload(entry, platform)
        for platform in PLATFORMS
    )
    if DOMAIN in hass.data:
        del hass.data[DOMAIN]
    return unload_ok


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """配置变更时重载集成。"""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config: ConfigEntry, device: DeviceEntry
) -> bool:
    """移除设备（暂不支持单设备移除，返回 False）。"""
    _LOGGER.warning("tcl_ac: 暂不支持单独移除设备，请通过选项流排除")
    return False


# ──────────────── 平台 setup 函数（供各平台调用） ────────────────

def get_platform_devices(
    hass: HomeAssistant, target_category: str | None = None
) -> list[dict]:
    """从 hass.data 获取设备列表，可选按类型过滤。

    各平台在 async_setup_entry 中调用此函数获取自己负责的设备。
    """
    devices = hass.data.get(DOMAIN, {}).get("devices", [])
    if target_category is None:
        return devices
    return [d for d in devices if d.get("category") == target_category]
