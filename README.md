# TCL 空调 Home Assistant 集成（tcl_ac）

部分 TCL 空调在微信小程序内标记为"设备仅支持 TCL App 控制"（`weChatControl: "0"`），通用小程序集成无法接入。本集成复用 App 登录通道的 token，将控制请求 `source` 伪装为 App 直接下发指令，支持状态查询、开关机、调温（16~31°C）、模式/风速/摆风控制。支持 config_flow UI 添加，可选填账号密码启用 refreshToken 自动续期。

## 原理

小程序与 App 登录均走 `cn.account.tcl.com`，token 通用。TCL 仅在设备级锁死小程序通道（`weChatControl: "0"`），但状态查询不受限。本集成以小程序 token 认证，控制请求 `source=app`、UA `TCLPlus/2.6.1`，绕过设备级限制下发指令。

## 安装

1. HACS → 自定义仓库，添加 `https://github.com/<用户名>/tcl-ac-ha`，类别 Integration
2. 下载 TCL AC → 重启 HA
3. 设置 → 设备与服务 → 添加集成 → 搜 TCL AC
4. 填 `device_id`（必填）；`username`/`password` 可选，填则启用自动续期
5. 提交，实体 `climate.tcl_空调_<device_id>` 出现

## Token 获取

微信小程序登录 token 与 App 通用。用仓库 `grab_token.py`（mitmproxy 拦截小程序登录）提取，写入 HA `/config/tcl_token.json`。

```bash
python -m venv venv
venv\Scripts\pip install mitmproxy requests
venv\Scripts\mitmdump.exe --listen-port 18888   # 生成 CA 后 Ctrl+C
certutil.exe -addstore -user "Root" "$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.cer"
venv\Scripts\python.exe grab_token.py            # 微信电脑版打开 TCL 小程序触发登录
```

`device_id` 用 `verify_token.py` 查（`category: AC` 的 `deviceId`）。

`/config` 属主为 root，用 HA 内 Studio Code Server / File editor 或 Samba 写入，勿用飞牛文件管理器。

## 续期

- accessToken（~1h）：轮询自动 refresh。
- refreshToken（~60天）：填账号密码则失效时自动重登换发并写回 `tcl_token.json`；未填则过期后重跑 `grab_token.py`。
- 账号密码以 RSA-1024 加密（明文密码不出本机），仅存 HA 配置库。

## 排查

- 实体未出现：查日志 `tcl_ac`，多为 device_id 未配或 token 失效。
- 控制失败：试将 `const.py` 的 `CONTROL_SOURCE` 改为 `"TCL+"`。
- 状态超时：确认容器可访问 `io.zx.tcljd.com`。

## 安全

`tcl_token.json` 含 refreshToken，勿入仓库。本仓库不含该文件。
