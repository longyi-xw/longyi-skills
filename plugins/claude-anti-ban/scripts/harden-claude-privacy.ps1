<#
.SYNOPSIS
    Claude Code 账号防封禁与隐私网络加固脚本
.DESCRIPTION
    针对 Anthropic 严格的地域与遥测风控策略，执行系统层、应用层与配置层的全套加固：
    1. 注入 Claude Code 禁用遥测与非必要流量环境变量（静音 Datadog/GrowthBook/Sentry/OTEL）
    2. 切换系统时区以匹配节点出口 IP（如新加坡 Singapore Standard Time，保持 UTC+8 不变）
    3. 清洗 settings.json 中的国内镜像源特征（如 npmmirror）
    4. 检验网络出口 IP、DNS 解析与 claude auth 状态
#>

[CmdletBinding()]
param(
    [string]$TargetTimezone = "Singapore Standard Time",
    [switch]$SkipTimezone,
    [switch]$SetUserEnv,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Claude Code 账号防封与隐私环境加固工具" -ForegroundColor Cyan
Write-Host "=========================================`n" -ForegroundColor Cyan

# 1. 查找有效配置目录
$configDirs = @()
if ($env:CLAUDE_CONFIG_DIR -and (Test-Path $env:CLAUDE_CONFIG_DIR)) {
    $configDirs += $env:CLAUDE_CONFIG_DIR
}
$defaultDir = Join-Path $env:USERPROFILE ".claude"
if (Test-Path $defaultDir) {
    if ($configDirs -notcontains $defaultDir) {
        $configDirs += $defaultDir
    }
}

if ($configDirs.Count -eq 0) {
    Write-Warning "未找到 Claude Code 配置目录（%USERPROFILE%\.claude 或 CLAUDE_CONFIG_DIR）。"
}

# 遥测静音变量集
$privacyEnv = [ordered]@{
    "DISABLE_TELEMETRY"                       = "1"
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"= "1"
    "DO_NOT_TRACK"                            = "1"
    "DISABLE_ERROR_REPORTING"                 = "1"
    "DISABLE_GROWTHBOOK"                      = "1"
    "OTEL_SDK_DISABLED"                       = "true"
    "OTEL_TRACES_EXPORTER"                    = "none"
    "OTEL_METRICS_EXPORTER"                   = "none"
    "OTEL_LOGS_EXPORTER"                      = "none"
    "LANG"                                    = "en_US.UTF-8"
    "LC_ALL"                                  = "en_US.UTF-8"
}

if (-not $VerifyOnly) {
    # 2. 更新 settings.json
    foreach ($dir in $configDirs) {
        $settingsFile = Join-Path $dir "settings.json"
        if (Test-Path $settingsFile) {
            Write-Host "[1/4] 更新配置文件: $settingsFile" -ForegroundColor Yellow
            try {
                $content = Get-Content -Path $settingsFile -Raw -Encoding utf8
                $json = $content | ConvertFrom-Json

                if (-not $json.PSObject.Properties['env']) {
                    $json | Add-Member -NotePropertyName "env" -NotePropertyValue ([PSCustomObject]@{})
                }

                foreach ($k in $privacyEnv.Keys) {
                    if ($json.env.PSObject.Properties[$k]) {
                        $json.env.$k = $privacyEnv[$k]
                    } else {
                        $json.env | Add-Member -NotePropertyName $k -NotePropertyValue $privacyEnv[$k]
                    }
                }

                # 清洗 autoMode 中的国内源特征
                if ($json.PSObject.Properties['autoMode'] -and $json.autoMode.PSObject.Properties['environment']) {
                    $envLines = @($json.autoMode.environment)
                    for ($i = 0; $i -lt $envLines.Count; $i++) {
                        if ($envLines[$i] -match "npmmirror\.com") {
                            $envLines[$i] = $envLines[$i] -replace "registry\.npmmirror\.com", "registry.npmjs.org"
                            Write-Host "  -> 已清洗 autoMode 中的 npmmirror 国内镜像标识" -ForegroundColor Green
                        }
                    }
                    $json.autoMode.environment = $envLines
                }

                $newJson = $json | ConvertTo-Json -Depth 20
                Set-Content -Path $settingsFile -Value $newJson -Encoding utf8
                Write-Host "  -> 成功写入静音环境变量与清洗配置。" -ForegroundColor Green
            } catch {
                Write-Warning "更新 $settingsFile 失败: $_"
            }
        }
    }

    # 3. 写入 Windows 用户全局环境变量
    if ($SetUserEnv) {
        Write-Host "`n[2/4] 写入 Windows 用户级全局环境变量..." -ForegroundColor Yellow
        foreach ($k in $privacyEnv.Keys) {
            [System.Environment]::SetEnvironmentVariable($k, $privacyEnv[$k], "User")
        }
        Write-Host "  -> 用户全局环境变量设置完成（子进程与新终端均将默认生效）。" -ForegroundColor Green
    } else {
        Write-Host "`n[2/4] 跳过写入全局用户环境变量（可通过 -SetUserEnv 显式开启）。" -ForegroundColor DarkGray
    }

    # 4. 时区同步
    if (-not $SkipTimezone -and $TargetTimezone) {
        Write-Host "`n[3/4] 检查系统时区设置..." -ForegroundColor Yellow
        $currentTz = (tzutil /g).Trim()
        if ($currentTz -ne $TargetTimezone) {
            Write-Host "  当前时区: $currentTz -> 切换为: $TargetTimezone" -ForegroundColor Cyan
            try {
                tzutil /s "$TargetTimezone"
                Write-Host "  -> 时区成功切换为 $TargetTimezone" -ForegroundColor Green
            } catch {
                Write-Warning "时区切换失败，可能需要管理员权限: $_"
            }
        } else {
            Write-Host "  -> 当前时区已是 $TargetTimezone，无需修改。" -ForegroundColor Green
        }
    }
}

# 5. 验证与诊断
Write-Host "`n[4/4] 正在执行环境安全与网络诊断..." -ForegroundColor Yellow

# 5.1 检查出口 IP
try {
    $ipInfo = Invoke-RestMethod -Uri "https://ipinfo.io/json" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  出口 IP      : $($ipInfo.ip)" -ForegroundColor White
    Write-Host "  出口地区    : $($ipInfo.country) - $($ipInfo.city) ($($ipInfo.org))" -ForegroundColor White
    Write-Host "  IP 对应时区 : $($ipInfo.timezone)" -ForegroundColor White
} catch {
    Write-Host "  出口 IP 检测超时或未连通代理，请检查 TUN 模式。" -ForegroundColor Red
}

# 5.2 检查系统与运行时时区
$sysTz = (tzutil /g).Trim()
Write-Host "  系统时区    : $sysTz" -ForegroundColor White
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeTz = node -e "console.log(Intl.DateTimeFormat().resolvedOptions().timeZone)" 2>$null
    Write-Host "  Node.js 时区: $nodeTz" -ForegroundColor White
}

# 5.3 检查 Claude 遥测禁用状态
if (Get-Command claude -ErrorAction SilentlyContinue) {
    try {
        $claudeAuthRaw = claude auth status 2>$null
        if ($claudeAuthRaw -match 'analyticsDisabled["\s:]+true') {
            Write-Host "  Claude 遥测 : 已彻底禁用 (analyticsDisabled: true) [SAFE]" -ForegroundColor Green
        } else {
            Write-Host "  Claude 遥测 : 仍处于启用状态 [WARNING]" -ForegroundColor Red
        }
    } catch {
        Write-Host "  无法获取 claude auth status: $_" -ForegroundColor DarkGray
    }
}

Write-Host "`n加固与诊断完成！" -ForegroundColor Cyan
