---
name: claude-anti-ban
description: Claude Code 账号防封禁与网络隐私加固规范。当用户询问 Claude / Claude Code 防封、账号封禁原因、风控排查、关闭后台遥测与网络数据采集、修改系统时区以匹配代理出口 IP、检测与修复 DNS/IPv6 泄漏、清理本地国内镜像源特征等问题，或需要为 Claude Code 配置防封环境时使用。包含三层立体防护工作流与一键加固脚本。
---

# Claude Code 账号防封禁与网络隐私加固规范

针对 Anthropic 针对未开放地区（如中国大陆、香港、澳门等）的使用限制与风控策略，提供三维立体加固方案：**应用遥测静音**、**系统指纹对齐**与**网络层防泄漏**。

---

## 核心防封理念：三层立体加固体系

Anthropic 的账号风控通常是由**多维特征的综合异常评分**触发，单做一层防护极易被其他维度的泄漏击穿：

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 应用遥测层：切断非业务后台上报 (Datadog, GrowthBook, OTEL) │
├─────────────────────────────────────────────────────────────┤
│ 2. 系统指纹层：时区对齐 IP、统一英文 Locale、清洗境内镜像特征 │
├─────────────────────────────────────────────────────────────┤
│ 3. 网络分流层：TUN 模式接管、Fake-IP 杜绝 DNS 泄漏、双栈防护 │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速一键加固脚本

本技能内置了全自动检测与加固脚本，位于 `scripts/harden-claude-privacy.ps1`：

```powershell
# 1. 仅执行安全与网络泄漏自检（不修改任何系统设置）
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\skills\catalog\core\claude-anti-ban\scripts\harden-claude-privacy.ps1" -VerifyOnly

# 2. 执行完整加固（默认切换新加坡时区、注入静音环境变量、更新 settings.json、写入用户全局环境变量）
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\skills\catalog\core\claude-anti-ban\scripts\harden-claude-privacy.ps1" -SetUserEnv

# 3. 指定目标时区（如使用美西节点时切换为太平洋时区）
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\skills\catalog\core\claude-anti-ban\scripts\harden-claude-privacy.ps1" -TargetTimezone "Pacific Standard Time" -SetUserEnv
```

---

## 详细工作流与手动加固指引

当遇到用户咨询或需要按步骤执行加固时，按以下五个阶段推进：

### 阶段一：现状诊断与泄漏检测

在开始前先采集当前环境的关键指标：

```powershell
# 1. 检查出口 IP、地区与 ASN
curl -s https://ipinfo.io/json

# 2. 检查 DNS 是否命中 Fake-IP（安全应返回 198.18.x.x）
Resolve-DnsName api.anthropic.com

# 3. 检查系统时区与 Node 运行时识别时区
tzutil /g
node -e "console.log(Intl.DateTimeFormat().resolvedOptions().timeZone)"

# 4. 检查 Claude Code 遥测开关状态
claude auth status
```

### 阶段二：应用层遥测与非必要流量阻断

Claude Code 底层内建了 Datadog 日志、GrowthBook 实验上报与 OpenTelemetry 追踪。需在配置中注入静音环境变量：

1. **定位有效配置文件**：
   - 优先检查 `$env:CLAUDE_CONFIG_DIR\settings.json`（若设置了缓存自定义目录）。
   - 同时维护默认目录 `%USERPROFILE%\.claude\settings.json`。

2. **注入静音环境变量**：
   确保 `settings.json` 中的 `"env"` 节点包含以下键值：
   ```json
   {
     "env": {
       "DISABLE_TELEMETRY": "1",
       "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
       "DO_NOT_TRACK": "1",
       "DISABLE_ERROR_REPORTING": "1",
       "DISABLE_GROWTHBOOK": "1",
       "OTEL_SDK_DISABLED": "true",
       "OTEL_TRACES_EXPORTER": "none",
       "OTEL_METRICS_EXPORTER": "none",
       "OTEL_LOGS_EXPORTER": "none",
       "LANG": "en_US.UTF-8",
       "LC_ALL": "en_US.UTF-8"
     }
   }
   ```

3. **设置 Windows 用户全局环境变量**：
   为了使新打开的终端、IDE（VS Code / Cursor / Antigravity）等子进程均默认继承，执行：
   ```powershell
   [System.Environment]::SetEnvironmentVariable("DISABLE_TELEMETRY", "1", "User")
   [System.Environment]::SetEnvironmentVariable("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1", "User")
   [System.Environment]::SetEnvironmentVariable("DO_NOT_TRACK", "1", "User")
   [System.Environment]::SetEnvironmentVariable("DISABLE_ERROR_REPORTING", "1", "User")
   [System.Environment]::SetEnvironmentVariable("DISABLE_GROWTHBOOK", "1", "User")
   ```

4. **验证**：运行 `claude auth status`，确认输出中 `"analyticsDisabled": true`。

### 阶段三：系统指纹对齐与特征清洗

1. **系统时区匹配出口节点**：
   - **推荐实践（新加坡节点）**：新加坡与中国同属 **UTC+8** 时区。执行以下命令切换为新加坡时区后，电脑表盘时间**无任何时差变化**，而运行时报告的 IANA 时区将精准转为 `Asia/Singapore`：
     ```powershell
     tzutil /s "Singapore Standard Time"
     ```
   - 若使用日本节点，可设为 `Tokyo Standard Time`（UTC+9）；若使用美西节点，可设为 `Pacific Standard Time`（UTC-8）。

2. **清洗配置文件与提示词中的国内镜像痕迹**：
   - 检查 `settings.json` 中的 `autoMode.environment` 字段。
   - 若包含 `"**Internal package registry**: registry.npmmirror.com"`，必须替换为官方源 `"**Internal package registry**: registry.npmjs.org"` 或将其移除，防止该上下文随 Prompt 发往服务端。

3. **设置终端语言环境**：
   - 保证 `LANG` 与 `LC_ALL` 为 `en_US.UTF-8`，避免 CLI 工具报错抛出中文 Windows 错误码而隐式暴露本地语言。

### 阶段四：网络层与 DNS 防泄漏

确保所有 Anthropic 相关流量均走代理内核，绝不产生本地回落：

1. **启用 TUN 模式 + Fake-IP**：
   - 确保使用 Clash Verge Rev / Mihomo / Sing-box 并开启 TUN 虚拟网卡模式。
   - 确保启用 `enhanced-mode: fake-ip`。

2. **配置前置置顶分流规则 (Prepend Rules)**：
   在代理客户端的增强规则中将以下域名置顶：
   ```yaml
   prepend:
     - DOMAIN-SUFFIX,anthropic.com,🚀 节点选择
     - DOMAIN-SUFFIX,claude.ai,🚀 节点选择
     - DOMAIN-SUFFIX,claude.com,🚀 节点选择
   ```

3. **双栈检查 (IPv6)**：
   运行 `curl -s https://www.cloudflare.com/cdn-cgi/trace`，若输出的 `ip=` 为 IPv6 地址，通过 `curl -s https://ipinfo.io/<ipv6>/json` 确认该 IPv6 亦归属于代理服务商（如新加坡），而非本地电信/联通真实 IPv6。

---

## 深入参考文档

- **五大风控维度深度剖析**：请阅读 [risk-vectors.md](references/risk-vectors.md)，深入了解机房 IP 评分、风控连坐、DNS 污染与支付关联风险。
- **代理与 DNS 分流配置手册**：请阅读 [proxy-and-dns-rules.md](references/proxy-and-dns-rules.md)，查阅 Clash Verge Rev、Surge、Sing-box 的详细配置示例。
