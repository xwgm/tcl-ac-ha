# TCL 空调接入 Home Assistant（绕过"仅 App 控制"限制）

让**"仅支持 TCL App 控制"**的 TCL 空调接入 Home Assistant：能读真实运行状态、能开关机 / 调温（16~31°C）/ 切换模式（制冷·制热·自动·除湿·送风）/ 风速 / 摆风。**零额外硬件成本。**

> 适用场景：你的空调在微信小程序里显示"设备仅支持 TCL App 控制"、涂鸦 App 搜不到、原版小程序集成（ndwzy / qwqqq6）加载不出设备。

---

## 原理（一句话）

TCL 在**设备级**锁死了微信小程序通道（字段 `weChatControl: "0"`）。但小程序和 App 登录走的是同一个 `cn.account.tcl.com`，token 通用。

本集成用 **微信小程序账号 token 认证** + 把**控制请求的 `source` 伪装成 App**（`source=app`、UA=`TCLPlus/2.6.1`），绕过设备级限制。状态查询不受限，因此能读空调真实运行状态。

---

## Token 自动续期（重点）

组件内部有两层续期，基本做到**零维护**：

1. **accessToken（~1 小时）**：每次轮询自动用 `refreshToken` 换新，你无感。
2. **refreshToken（~60 天）**：
   - **填了账号密码 = 全自动**：`refreshToken` 失效时，组件用你的 TCL 账号密码（RSA 加密后登录）自动换发新 token 并写入 `/config/tcl_token.json`，永久不用手动抓包。
   - **没填账号密码 = 需手动**：`refreshToken` 过期后组件会在日志报错提示，此时重跑一次 `grab_token.py` 覆盖 `tcl_token.json` 即可。

> 账号密码登录采用 TCL App 内置的 **RSA-1024 公钥加密**（密码先 MD5 再整体加密，明文密码不出本机），传输走 HTTPS。密码只存在你的 `configuration.yaml` 本地文件里，不会进代码或公开仓库。

---

## 一、HACS 安装

1. HA → HACS → 右上角菜单 → **自定义仓库**
2. 仓库 URL 填你自己的：`https://github.com/<你的GitHub用户名>/tcl-ac-ha`
3. 类别选 **Integration** → 添加
4. HACS 里搜 **TCL AC (App-controlled)** → 下载 → **重启 HA**

> 组件只含代码，**不含 token**。token 和 device_id 需你自行提供（见下）。

---

## 二、拿到 TCL token（在你的 Windows 上）

仓库根目录的 `grab_token.py` 用 mitmproxy 拦截微信小程序登录请求、自动提取 token 写入 `tcl_token.json`。

**简化步骤：**
```bash
# 1. 建 venv 装依赖
python -m venv venv
venv\Scripts\pip install mitmproxy requests

# 2. 生成并信任 mitmproxy CA 证书（首次）
venv\Scripts\mitmdump.exe --listen-port 18888
#  跑几秒后 Ctrl+C，证书已生成在 %USERPROFILE%\.mitmproxy\
#  用 certutil 装进系统信任库（详见下方"证书安装"）

# 3. 开系统代理 127.0.0.1:8888，运行抓包
venv\Scripts\python.exe grab_token.py

# 4. 打开微信电脑版 → TCL 小程序，刷新设备列表触发一次登录
# 5. 生成 tcl_token.json
```

**证书安装（管理员 PowerShell）：**
```powershell
certutil.exe -addstore -user "Root" "$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.cer"
```

---

## 三、把 token 放进 HA 的 /config（重要）

> ⚠️ **为什么你之前在飞牛文件管理器里报"不是用户可以进行的操作"**
> 飞牛的 `/config` 目录属主是 `root:root`，飞牛文件管理器用的是普通用户，没写权限。
> **解决：用 HA 内部的文件工具来写，不要用飞牛文件管理器。**

任选其一（以 HA 进程权限运行，能写 `/config`）：
- HA → 加载项 → **Studio Code Server**（或 **File editor**）→ 新建 `/config/tcl_token.json`，把 Windows 上生成的 `tcl_token.json` 内容粘进去保存
- 或开 HA 的 **Samba 共享**，从 Windows 网络邻居写入 `/config/tcl_token.json`

---

## 四、获取 device_id

在 Windows 上（用刚抓到的 token）：
```bash
venv\Scripts\python.exe verify_token.py
```
列出账号下设备，找 `category: AC` 那台的 `deviceId`（示例书房空调是 `36376945`）。

---

## 五、配置 configuration.yaml

同样用 **Studio Code Server / File editor** 打开 `/config/configuration.yaml`，追加：
```yaml
tcl_ac:
  device_id: "36376945"   # 换成你上一步查到的 deviceId
  # 以下两项填了就能永久自动续期，不填则 refreshToken 过期需手动重抓
  username: "13800138000" # ← 你的 TCL 账号（手机号）
  password: "你的TCL密码"  # ← 你的 TCL 密码（明文，仅存于本地）
```
保存 → **重启 HA**。

> device_id / username / password 都写在 configuration.yaml 里，HACS 更新组件不会覆盖它们。
> 只填 device_id、不填账号密码 = 仍可用，只是 refreshToken 过期后需手动重抓（见上「Token 自动续期」）。

---

## 六、验证

HA → 设置 → 设备与服务 → 实体 → 搜「TCL」，应出现 `climate.tcl_ac_climate` 卡片，可控制并显示室温。

---

## 维护

- **token 约 60 天过期**：到期后在 Windows 重跑 `grab_token.py`（微信小程序触发一次），把新 `tcl_token.json` 覆盖到 HA 的 `/config/` 即可，不用重装组件。
- HACS 更新组件不会影响你的 `device_id` 配置。

---

## 安全提示

- `tcl_token.json` 含你的 TCL 账号 refreshToken，**切勿提交到公开仓库或发给他人**。本仓库不含该文件。
- 飞牛 SSH 等敏感密码不要明文留存。

---

## 故障排查

- **实体没出现**：查 HA 日志里 `tcl_ac`，多半是 `device_id` 没配或 token 失效（重新抓）。
- **控制返回失败**：把 `custom_components/tcl_ac/const.py` 的 `CONTROL_SOURCE` 改成 `"TCL+"` 重试；或抓手机 TCL 智家 App 真实流量确认 `source` 实际值。
- **状态超时**：确认 HA 容器能访问 `io.zx.tcljd.com`（飞牛 Docker 一般默认通）。
