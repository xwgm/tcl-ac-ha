"""TCL AC config_flow（v2.0：只填手机号和密码，自动枚举全量设备）。"""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback

from .const import DOMAIN
from .api import TclApi

_LOGGER = logging.getLogger(__name__)


class TclConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            username = (user_input.get("username") or "").strip()
            password = (user_input.get("password") or "").strip()

            if not username:
                errors["username"] = "username_required"
            elif not password:
                errors["password"] = "password_required"
            else:
                # 防止同一手机号账号重复添加
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()
                # 尝试登录验证凭据有效性
                try:
                    api = TclApi()
                    token = await self.hass.async_add_executor_job(
                        api.login_by_password, username, password
                    )
                    return self.async_create_entry(
                        title=f"TCL 账号 ({username})",
                        data={
                            "username": username,
                            "password": password,
                            "account_id": api._account_id,
                            "token": token,
                        },
                    )
                except Exception as err:
                    _LOGGER.warning("TCL 登录失败: %s", err)
                    errors["base"] = "auth_failed"

        data_schema = vol.Schema({
            vol.Required("username"): str,
            vol.Required("password"): str,
        })
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """选项流：重新配置账号密码。"""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            username = (user_input.get("username") or "").strip()
            password = (user_input.get("password") or "").strip()

            if not username:
                errors["username"] = "username_required"
            elif not password:
                errors["password"] = "password_required"
            else:
                try:
                    api = TclApi()
                    await self.hass.async_add_executor_job(
                        api.login_by_password, username, password
                    )
                    new_data = dict(self._entry.data)
                    new_data["username"] = username
                    new_data["password"] = password
                    new_data["account_id"] = api._account_id
                    new_data["token"] = api._token
                    self.hass.config_entries.async_update_entry(
                        self._entry.entry_id, data=new_data
                    )
                    return self.async_create_entry(title="", data={})
                except Exception as err:
                    _LOGGER.warning("TCL 登录失败: %s", err)
                    errors["base"] = "auth_failed"

        data = self._entry.data or {}
        data_schema = vol.Schema({
            vol.Required(
                "username",
                default=data.get("username", ""),
            ): str,
            vol.Required("password", default=data.get("password", "")): str,
        })
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
