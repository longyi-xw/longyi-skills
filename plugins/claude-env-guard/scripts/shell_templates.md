# Native Shell & Browser Opener Templates

Use these templates alongside `claude_guard_template.py` (or standalone when Python is unavailable), and for compiling the isolated `BROWSER` opener so `claude` CLI OAuth logins (`claude auth login` / `/login`) never fall back to the host's non-isolated browser.

## 1. macOS / Linux Isolated `BROWSER` Opener (`claude-browser-opener.sh`)

Mark executable with `chmod +x claude-browser-opener.sh` and place next to `claude_guard.py` (or export `BROWSER=/path/to/claude-browser-opener.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

URL="${1:-}"
case "$URL" in
  http://*|https://*) ;;
  *) exit 1 ;;
esac

PROXY_URL="${CLAUDE_GUARD_PROXY:-http://127.0.0.1:7897}"
PROFILE_DIR="${CLAUDE_GUARD_PROFILE:-$HOME/.claude-chrome-profile}"
mkdir -p "$PROFILE_DIR"

COMMON_ARGS=(
  "--user-data-dir=$PROFILE_DIR"
  "--proxy-server=$PROXY_URL"
  "--lang=en-US"
  "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"
  "--enforce-webrtc-ip-permission-check"
  "--no-first-run"
  "$URL"
)

if [[ "$(uname)" == "Darwin" ]]; then
  CHROME_BIN="${CLAUDE_GUARD_CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
  nohup "$CHROME_BIN" "${COMMON_ARGS[@]}" >/dev/null 2>&1 &
else
  CHROME_BIN="${CLAUDE_GUARD_CHROME:-$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || command -v chromium-browser)}"
  nohup "$CHROME_BIN" "${COMMON_ARGS[@]}" >/dev/null 2>&1 &
fi
exit 0
```

## 2. Windows Isolated `BROWSER` Opener Compilation (`claude-browser-opener.exe`)

On Windows, Claude Code CLI invokes `BROWSER` with `shell: false`, so `.cmd`/`.bat` wrappers cannot be used directly; compile a native Win32/GUI executable from either template in `scripts/`:

- **With Rust** (preferred if installed):
  ```powershell
  rustc -O -C strip=symbols claude_browser_opener.rs -o claude-browser-opener.exe
  ```
- **Without Rust** (uses built-in Windows .NET Framework `csc.exe`, zero dependencies):
  ```powershell
  C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:winexe /nologo /out:claude-browser-opener.exe claude_browser_opener.cs
  ```

Both spawn Chrome detached with `--user-data-dir`, `--proxy-server`, `--lang=en-US`, and WebRTC UDP blocking, then exit `0` immediately so CLI OAuth callback listening continues uninterrupted.

## 3. macOS / Linux Bash Launcher (`claude-guard.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROXY_PORT="${CLAUDE_PROXY_PORT:-7897}"
CLASH_API="${CLASH_CONTROLLER:-127.0.0.1:9097}"
CLASH_SECRET="${CLASH_SECRET:-}"
CLAUDE_GROUP="🔒 Claude-固定出口"
TARGET_NODE="${2:-}"

export http_proxy="http://127.0.0.1:${PROXY_PORT}"
export https_proxy="http://127.0.0.1:${PROXY_PORT}"
export all_proxy="socks5://127.0.0.1:${PROXY_PORT}"

# Optional: Switch Clash node via REST API if target node is passed
if [[ -n "$TARGET_NODE" ]]; then
  ENCODED_GROUP=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$CLAUDE_GROUP")
  curl -s -X PUT "http://${CLASH_API}/proxies/${ENCODED_GROUP}" \
    -H "Authorization: Bearer ${CLASH_SECRET}" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${TARGET_NODE}\"}" >/dev/null || true
fi

IP_INFO=$(curl -s --max-time 5 https://ipinfo.io/json || true)
if [[ -z "$IP_INFO" ]]; then
  echo "❌ 无法通过 127.0.0.1:${PROXY_PORT} 连接代理网络，已中止启动！"
  exit 1
fi

COUNTRY=$(echo "$IP_INFO" | grep -o '"country": *"[^"]*"' | cut -d'"' -f4)
TIMEZONE=$(echo "$IP_INFO" | grep -o '"timezone": *"[^"]*"' | cut -d'"' -f4)
IP_ADDR=$(echo "$IP_INFO" | grep -o '"ip": *"[^"]*"' | cut -d'"' -f4)

if [[ "$COUNTRY" == "CN" || "$COUNTRY" == "HK" || "$COUNTRY" == "MO" ]]; then
  echo "🚨 危险拦截: 当前出口为 ${COUNTRY} (${IP_ADDR})，已拒绝启动！"
  exit 1
fi

echo "✅ 校验通过: IP=${IP_ADDR} | 国家=${COUNTRY} | 时区=${TIMEZONE}"
export TZ="${TIMEZONE}"
export CLAUDE_GUARD_PROXY="http://127.0.0.1:${PROXY_PORT}"
export CLAUDE_GUARD_PROFILE="$HOME/.claude-chrome-profile"
if [[ -x "$SCRIPT_DIR/claude-browser-opener.sh" ]]; then
  export BROWSER="$SCRIPT_DIR/claude-browser-opener.sh"
fi

MODE="${1:-web}"
if [[ "$MODE" == "web" ]]; then
  CHROME_PROFILE="$CLAUDE_GUARD_PROFILE"
  if [[ "$(uname)" == "Darwin" ]]; then
    open -na "Google Chrome" --args \
      --user-data-dir="$CHROME_PROFILE" \
      --proxy-server="http://127.0.0.1:${PROXY_PORT}" \
      --lang="en-US" \
      --force-webrtc-ip-handling-policy="disable_non_proxied_udp" \
      --enforce-webrtc-ip-permission-check \
      "https://claude.ai"
  else
    google-chrome \
      --user-data-dir="$CHROME_PROFILE" \
      --proxy-server="http://127.0.0.1:${PROXY_PORT}" \
      --lang="en-US" \
      --force-webrtc-ip-handling-policy="disable_non_proxied_udp" \
      --enforce-webrtc-ip-permission-check \
      "https://claude.ai" >/dev/null 2>&1 &
  fi
elif [[ "$MODE" == "cli" ]]; then
  export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
  export DISABLE_TELEMETRY=1
  export DISABLE_ERROR_REPORTING=1
  export DISABLE_FEEDBACK_COMMAND=1
  export CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY=1
  export CLAUDE_CODE_ATTRIBUTION_HEADER=0
  claude "${@:2}"
fi
```

## 4. Windows PowerShell Wrapper Template (`claude-guard.ps1`)

> **Windows Encoding Gotcha**: Save `.ps1` files containing Chinese/emoji literals (`🇸🇬`, `🔒`) as **UTF-8 with exactly ONE BOM (`EF BB BF`) + CRLF** so both Windows PowerShell 5.1 and PowerShell 7 parse parameters cleanly (avoid double BOMs). For double-clickable `.cmd` wrappers, include `chcp 65001 >nul` and `if errorlevel 1 pause`.

```powershell
param(
    [ValidateSet("web", "cli", "check", "reset-account")]
    [string]$Mode = "web",
    [string]$Node = "",
    [int]$ProxyPort = 0,
    [ValidateSet("strict", "balanced")]
    [string]$Telemetry = "strict",
    [switch]$KeepGlobal,
    [switch]$SyncSystemTimezone,
    [switch]$DryRun,
    [switch]$Yes,
    [switch]$IncludeWebSession,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$GuardScript = Join-Path $PSScriptRoot "claude_guard.py"

if ($SyncSystemTimezone) {
    $DetectPort = if ($ProxyPort -gt 0) { $ProxyPort } else { 7897 }
    $IanaToWinTz = @{
        "America/Los_Angeles" = "Pacific Standard Time"
        "America/Vancouver"   = "Pacific Standard Time"
        "America/Denver"      = "Mountain Standard Time"
        "America/Chicago"     = "Central Standard Time"
        "America/New_York"    = "Eastern Standard Time"
        "America/Toronto"     = "Eastern Standard Time"
        "Europe/London"       = "GMT Standard Time"
        "Europe/Berlin"       = "W. Europe Standard Time"
        "Europe/Amsterdam"    = "W. Europe Standard Time"
        "Europe/Paris"        = "Romance Standard Time"
        "Asia/Tokyo"          = "Tokyo Standard Time"
        "Asia/Seoul"          = "Korea Standard Time"
        "Asia/Singapore"      = "Singapore Standard Time"
        "Asia/Taipei"         = "Taipei Standard Time"
        "Australia/Sydney"    = "AUS Eastern Standard Time"
        "UTC"                 = "UTC"
    }
    try {
        $IpInfo = Invoke-RestMethod -Uri "https://ipinfo.io/json" -Proxy "http://127.0.0.1:$DetectPort" -TimeoutSec 6
        if ($IpInfo.timezone -and $IanaToWinTz.ContainsKey($IpInfo.timezone)) {
            $TargetWinTz = $IanaToWinTz[$IpInfo.timezone]
            if ((& tzutil /g).Trim() -ne $TargetWinTz) {
                & tzutil /s $TargetWinTz
                Write-Host "🕒 已同步 Windows 系统时区为: $TargetWinTz" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Warning "跳过系统时区同步预检: $_"
    }
}

$PyArgs = @($GuardScript, $Mode, "--telemetry", $Telemetry)
if ($Node) { $PyArgs += @("--node", $Node) }
if ($ProxyPort -gt 0) { $PyArgs += @("--port", "$ProxyPort") }
if ($KeepGlobal) { $PyArgs += "--keep-global" }
if ($DryRun) { $PyArgs += "--dry-run" }
if ($Yes) { $PyArgs += "--yes" }
if ($IncludeWebSession) { $PyArgs += "--include-web-session" }
if ($ExtraArgs) { $PyArgs += $ExtraArgs }

& python @PyArgs
exit $LASTEXITCODE
```
