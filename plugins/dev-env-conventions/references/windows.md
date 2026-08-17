# Windows 细则

核心诉求：**不装 C 盘**。系统盘重装即丢，且默认路径全在 `%LOCALAPPDATA%` / `%APPDATA%` 下。
下面用 `D:` 举例，换成任何非系统盘都成立。

## 目录地图

| 路径 | 用途 |
|------|------|
| `D:\software\scoop` | Scoop 根（git / vscode / fnm / uv / …） |
| `D:\software\nodejs` | 当前激活的 Node（版本管理器维护的符号链接） |
| `D:\software\nodejs-global` | npm / pnpm 全局包 |
| `D:\software\python` | uv 装的多版本 Python |
| `D:\software\caches` | npm / pnpm / yarn / pip / uv 缓存 |
| `D:\software\tools` | 工具 bin、`uv tool` 安装目录 |
| `D:\dev` | 业务代码仓库 |
| `D:\agents` | Agent 工作区 / 日志 / 配置 |
| `D:\skills` | skills 仓库 |
| `D:\tmp` | `TEMP` / `TMP` |

## Scoop

Scoop 免管理员、可整目录搬走，是 Windows 上首选。**装之前先定根目录**，装完再改要重装：

```powershell
[Environment]::SetEnvironmentVariable('SCOOP','D:\software\scoop','User')
$env:SCOOP = 'D:\software\scoop'
irm get.scoop.sh | iex

scoop install git fnm uv
scoop bucket add extras          # GUI 应用在这个 bucket
```

Scoop 里没有的（多为需要写系统注册表的安装包）用 `winget install <id>`。
winget 装的东西**不受 `SCOOP` 控制**，路径由安装包决定，装前确认它支持改安装目录。

## Node 版本管理

新机器用 **fnm**（跨平台一致，见 `SKILL.md` 第 4 节）：

```powershell
scoop install fnm
[Environment]::SetEnvironmentVariable('FNM_DIR','D:\software\fnm','User')
# 写进 $PROFILE
fnm env --use-on-cd | Out-String | Invoke-Expression

fnm install 22
fnm use 22
```

存量机器上的 **nvm-windows** 继续可用，但要清楚它和 POSIX 的 `nvm` 不是一个东西：

| 项 | nvm-windows | nvm（POSIX） |
|---|---|---|
| 切换机制 | 改一个符号链接（`NVM_SYMLINK`），全局生效 | 改当前 shell 的 PATH，逐 shell 生效 |
| `.nvmrc` | 不自动读 | `nvm use` 会读 |
| 权限 | 建符号链接需要管理员或开发者模式 | 不需要 |

关键环境变量：`NVM_HOME`（nvm 自身）、`NVM_SYMLINK`（当前激活版本的链接目标，要加进 PATH）。

```powershell
nvm list
nvm use 22.23.1
```

## 全局包与缓存重定向

Windows 上这些默认值都在 C 盘，**每一条都得显式设**（用户级环境变量）：

```powershell
$vars = @{
  npm_config_cache      = 'D:\software\caches\npm'
  PNPM_HOME             = 'D:\software\nodejs-global\pnpm'
  UV_CACHE_DIR          = 'D:\software\caches\uv'
  UV_PYTHON_INSTALL_DIR = 'D:\software\python'
  TEMP                  = 'D:\tmp'
  TMP                   = 'D:\tmp'
}
foreach ($k in $vars.Keys) { [Environment]::SetEnvironmentVariable($k, $vars[$k], 'User') }
```

改完**必须开新终端**才生效 —— 这是「命令找不到」最常见的原因。

## 目录联接（junction）

Windows 上把 C 盘的固定路径「引流」到 D 盘用目录联接，**不需要管理员权限**（符号链接才需要）：

```powershell
New-Item -ItemType Junction -Path 'C:\Users\me\AppData\Local\SomeApp' -Value 'D:\software\SomeApp'
```

适用场景：软件写死了安装路径、缓存目录不给改。做法是先把原目录挪到 D 盘，再在原位置建联接。
注意：junction 只能指向**本机的目录**（不能跨机器、不能指文件）；跨卷可以。

## PowerShell profile

| PowerShell 版本 | profile 路径 |
|---|---|
| 7+ | `~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` |
| 5.1 | `~\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` |

两者互不共享。`$PROFILE` 会给出当前进程用的那个。

存成 **UTF-8 带 BOM**：Windows PowerShell 5.1 读 `.ps1` 默认按系统 ANSI 解析，没 BOM 的话中文会乱码并直接导致语法错误。

## 迁移到新机器

1. 整个 `D:\software`、`D:\dev`、`D:\agents` 拷过去
2. 重设上面那批用户级环境变量（盘符若变，一并改）
3. `scoop reset *` 修复 shims，`fnm use <版本>` 重建链接
4. 复制 `$PROFILE`
