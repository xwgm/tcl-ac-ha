# TCL 空调 Home Assistant 集成（tcl_ac）

将 TCL 空调接入 Home Assistant，支持状态查询、开关机、调温（16~31°C）、模式/风速/摆风控制。支持 config_flow UI 添加，可选填账号密码启用 token 自动续期。

## 安装

1. HACS → 自定义仓库，添加 `https://github.com/<用户名>/tcl-ac-ha`，类别 Integration
2. 下载 TCL AC → 重启 HA
3. 设置 → 设备与服务 → 添加集成 → 搜 TCL AC
4. 填 `device_id`（必填）；`username`/`password` 可选，填则启用自动续期
5. 提交，实体 `climate.tcl_空调_<device_id>` 出现

## Token 获取

用仓库 `grab_token.py` 提取微信小程序登录 token，写入 HA `/config/tcl_token.json`。

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

- 填账号密码：token 过期时自动重登续期，无需手动操作。
- 未填账号密码：token 过期后重跑 `grab_token.py` 覆盖 `/config/tcl_token.json`。

## 排查

- 实体未出现：查日志 `tcl_ac`，多为 device_id 未配或 token 失效。
- 状态超时：确认容器网络可访问空调云服务。

## 安全

`tcl_token.json` 含账号凭据，勿入仓库。本仓库不含该文件。
