"""Select 平台：冰箱当前不创建模式选择实体（用户只需看当前温度与调整温度）。

保留此平台转发占位，便于后续按需恢复。
"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """冰箱不创建模式实体，本平台暂为空。"""
    return
