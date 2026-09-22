# 代理分流与 DNS 防泄漏配置最佳实践

本文档提供针对 Claude / Anthropic 系列域名的网络分流、Fake-IP 与防泄漏配置指南，涵盖 Clash Verge Rev (Mihomo)、Surge 与 Sing-box 等主流工具。

---

## 1. 核心分流域名清单

必须确保以下域名无论何时均强制命中代理节点分流策略，不得回落至 DIRECT 或 CN 直连：

```yaml
# Anthropic API & 业务网关
DOMAIN-SUFFIX,anthropic.com,🚀 节点选择
DOMAIN-SUFFIX,claude.ai,🚀 节点选择
DOMAIN-SUFFIX,claude.com,🚀 节点选择

# 遥测与监控（若未在客户端彻底禁用，务必走代理防直连泄漏）
DOMAIN-SUFFIX,datadoghq.com,🚀 节点选择
DOMAIN-SUFFIX,growthbook.io,🚀 节点选择
```

---

## 2. Clash Verge Rev / Mihomo 配置指南

### 2.1 开启 Fake-IP 模式
在 `dns_config.yaml` 或核心配置中确认启用 Fake-IP，彻底切断本地 DNS 上报：

```yaml
dns:
  enable: true
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter-mode: blacklist
  default-nameserver:
    - 223.6.6.6
    - 8.8.8.8
  nameserver:
    - 8.8.8.8
    - https://doh.pub/dns-query
```

### 2.2 配置增强前置规则 (Prepend Rules)
在订阅更新时，普通的订阅规则会被远程更新覆盖。为了避免 Anthropic 规则被意外冲掉，在 Clash Verge 的**增强规则 (Rules Template)** 中配置 `prepend`：

文件路径通常为：
`%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles\<profile-rule-id>.yaml`

内容模版：
```yaml
prepend:
  - DOMAIN-SUFFIX,anthropic.com,🚀 节点选择
  - DOMAIN-SUFFIX,claude.ai,🚀 节点选择
  - DOMAIN-SUFFIX,claude.com,🚀 节点选择

append: []
delete: []
```

### 2.3 开启 TUN 模式与严格路由 (Strict Route)
在 Verge 设置中开启 **TUN 模式**：
- 驱动模式选择：`Meta Tunnel (Wintun)`
- 开启 `严格路由 (Strict Route)` 与 `DNS 劫持 (DNS Hijack)`，保证即便某些 CLI 工具不走系统代理变量，也能被虚拟网卡全量捕获。

---

## 3. Sing-box 配置指南

在 `sing-box` 的 `route.rules` 中将 Anthropic 规则置于首位：

```json
{
  "route": {
    "rules": [
      {
        "domain_suffix": [
          "anthropic.com",
          "claude.ai",
          "claude.com"
        ],
        "outbound": "proxy-singapore"
      },
      {
        "geosite": "cn",
        "outbound": "direct"
      }
    ],
    "auto_detect_interface": true
  }
}
```

---

## 4. 常用网络诊断命令

在终端中快速自检当前网络环境是否存在泄漏：

### 4.1 检查 DNS 解析是否为 Fake-IP
```powershell
Resolve-DnsName api.anthropic.com
```
* **安全表现**：返回 `198.18.x.x` 地址，表明域名已被代理内核捕获接管。
* **危险表现**：返回公网真实 CDN IP 或解析失败。

### 4.2 检查 Cloudflare 边缘节点信息与 IPv6 状态
```powershell
curl -s https://www.cloudflare.com/cdn-cgi/trace
```
关键指标：
- `loc=SG`（出口国家代码需符合节点所在地区）
- `colo=SIN`（Cloudflare 访问的数据中心机房）
- `ip=`（检查若是 IPv6 地址，确保该 IPv6 亦属于代理提供商而非境内宽带）

### 4.3 检查公网 IP 归属与时区
```powershell
curl -s https://ipinfo.io/json
```
核对 `country`、`org` 以及 `timezone`。
