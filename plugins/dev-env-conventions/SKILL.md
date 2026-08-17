---
name: dev-env-conventions
description: 跨平台（Windows / macOS / Linux）本机开发环境约定：软件与代码装在哪、用哪个系统包管理器、Node/Python 多版本怎么管、缓存与环境变量往哪儿重定向、agent 与 skills 仓库放哪。当用户说「装个 xxx」「配一下开发环境」「新电脑装机」「命令找不到」「command not found」「PATH 没生效」「该用 brew 还是 apt」「node 版本怎么切」「pip 报 externally-managed」「装到哪个目录合适」「Mac 上怎么搞」，或要写跨平台装机 / 初始化脚本时使用。动手前先判定当前平台，再取对应那一列的路径与命令，绝不把某个平台的路径硬编码到另一个平台。Use this skill for cross-platform local dev-environment conventions on Windows, macOS, and Linux — install locations, system/Node/Python package managers, cache and env-var redirection, shell profile placement, and diagnosing PATH problems.
---

# 跨平台开发环境约定

**先判平台，再取路径。** 下面每张表都按 Windows / macOS / Linux 三列给值，取错列比不查还糟。
`D:\software` 这类盘符路径在 macOS/Linux 上根本不存在，`/opt/homebrew` 在 Windows 上同理。

## 1. 判定平台

```bash
# POSIX shell（macOS / Linux / WSL / Git Bash）
uname -s   # Darwin=macOS  Linux=Linux  MINGW64_NT-*/MSYS_NT-*=Windows 上的 Git Bash
uname -m   # arm64|aarch64 / x86_64
grep -qi microsoft /proc/version 2>/dev/null && echo WSL
```

```powershell
# PowerShell 7+：$IsWindows / $IsMacOS / $IsLinux
# Windows PowerShell 5.1 里这三个变量不存在 —— 取不到值就按 Windows 处理
if ($PSVersionTable.PSVersion.Major -lt 6 -or $IsWindows) { 'windows' }
elseif ($IsMacOS) { 'macos' } else { 'linux' }
```

```js
process.platform  // 'win32' | 'darwin' | 'linux'
process.arch      // 'x64' | 'arm64'
```

macOS 上还要区分芯片，Homebrew 前缀不同（Apple Silicon `/opt/homebrew`，Intel `/usr/local`）。
**永远用 `brew --prefix` 取值，不要硬编码。**

## 2. 通用原则（三平台共用）

1. 装到**用户级、可整体删除、可整体迁移**的目录，不碰系统托管路径。
2. 用包管理器装，不手动解压二进制往 PATH 里塞。
3. 运行时（Node/Python）一律交给版本管理器，不装「唯一一个系统版本」。
4. 缓存和全局包目录显式指向已知位置，别放任默认值散落。
5. 环境变量与版本管理器 init 写进 shell profile，不靠临时 `export`。

## 3. 逻辑根目录 → 各平台落点

先想「这东西属于哪个逻辑根」，再查这张表。写脚本时用逻辑根变量，别写死路径。

| 逻辑根 | 变量 | Windows | macOS | Linux |
|---|---|---|---|---|
| 工具与运行时 | `TOOLS_ROOT` | `D:\software` | `$(brew --prefix)` + `~/.local` | `~/.local` |
| 代码仓库 | `DEV_ROOT` | `D:\dev` | `~/Developer` | `~/dev` |
| 全局 CLI 可执行 | — | `D:\software\tools\bin` | `~/.local/bin` | `~/.local/bin` |
| 缓存 | — | `D:\software\caches` | `~/Library/Caches` | `${XDG_CACHE_HOME:-~/.cache}` |
| CLI 配置 | — | `%APPDATA%` | `~/.config` | `${XDG_CONFIG_HOME:-~/.config}` |
| GUI 应用 | — | `D:\software\<app>` | `/Applications`（brew cask 默认） | 发行版包管理器 / Flatpak |
| Agent 工作区 | `AGENTS_ROOT` | `D:\agents` | `~/.agents` | `~/.agents` |
| skills 仓库 | `SKILLS_ROOT` | `D:\skills` | `~/Developer/skills` | `~/dev/skills` |
| 临时目录 | `TMPDIR` / `TEMP` | `D:\tmp` | `$TMPDIR`（系统给的，别改） | `/tmp` |

**为什么 macOS/Linux 不照搬 `D:\software`：**

- macOS 自 Catalina 起 `/` 是只读的签名系统卷（SIP），想新建顶层目录得改 `/etc/synthetic.conf`。GUI 应用的约定位置就是 `/Applications`，命令行工具归 Homebrew 管自己的前缀，用户私有的进 `~/.local`。造一个 `/software` 既办不到也不该办。
- Linux 遵循 FHS + XDG：用户级的进 `~/.local` `~/.config` `~/.cache`，系统级的由发行版包管理器管 `/usr`。
- 两者都没有盘符概念，「装到非系统盘」这个 Windows 特有诉求在这里不存在 —— 对应诉求变成「装到 `$HOME` 下，不写系统目录」。

## 4. 包管理器矩阵

| 用途 | Windows | macOS | Linux |
|---|---|---|---|
| 系统 / 通用工具 | **Scoop**（免管理员，可换根目录）；Scoop 没有的用 `winget` | **Homebrew** | 发行版自带：`apt` / `dnf` / `pacman` / `zypper` / `apk`；跨发行版补充用 Homebrew 或 `mise` |
| Node 运行时多版本 | **fnm**（新机）/ nvm-windows（存量机保留） | **fnm** | **fnm** |
| Node 依赖 | `pnpm`（用 corepack 启用） | 同左 | 同左 |
| Python 解释器 / venv / 依赖 / 全局 CLI | **uv** | **uv** | **uv** |
| GUI 应用 | Scoop extras bucket / winget | `brew install --cask` | 发行版包管理器 / Flatpak |

**Node 为什么统一到 fnm**：`nvm`（POSIX）和 `nvm-windows` 是两个不相干的项目，命令、`.nvmrc` 支持、切换机制都不一样，跨机器脚本没法共用。fnm 三平台同一套命令，认 `.nvmrc` / `.node-version`，`--use-on-cd` 进目录自动切。存量的 nvm-windows 机器不必强迁，但**写脚本时不要假设 `nvm` 在三平台行为一致**。

**Python 为什么是 uv**：uv 三平台一套命令，同时管解释器安装、venv、依赖锁定和全局 CLI（`uv tool install`），不需要再叠 pyenv/pipx。

装机命令：

```powershell
# Windows —— 装 Scoop 前先把根目录指到非系统盘
[Environment]::SetEnvironmentVariable('SCOOP','D:\software\scoop','User')
$env:SCOOP='D:\software\scoop'; irm get.scoop.sh | iex
scoop install git fnm uv
```

```bash
# macOS —— 先装 Xcode 命令行工具，再装 Homebrew
xcode-select --install
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$($(brew --prefix)/bin/brew shellenv)"
brew install git fnm uv
```

```bash
# Linux（Debian/Ubuntu；其他发行版换包管理器，见 references/linux.md）
sudo apt update && sudo apt install -y build-essential curl git
curl -fsSL https://fnm.vercel.app/install | bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 5. 缓存与环境变量

| 变量 | 作用 | Windows（必须显式设） | macOS（默认即可） | Linux（默认即可） |
|---|---|---|---|---|
| `SCOOP` | Scoop 根 | `D:\software\scoop` | — | — |
| `FNM_DIR` | fnm 装的 Node | `D:\software\fnm` | `~/Library/Application Support/fnm` | `~/.local/share/fnm` |
| `npm_config_cache` | npm 缓存 | `D:\software\caches\npm` | `~/Library/Caches/npm` | `~/.cache/npm` |
| `PNPM_HOME` | pnpm 全局 bin | `D:\software\nodejs-global\pnpm` | `~/Library/pnpm` | `~/.local/share/pnpm` |
| `UV_CACHE_DIR` | uv 缓存 | `D:\software\caches\uv` | `~/Library/Caches/uv` | `~/.cache/uv` |
| `UV_PYTHON_INSTALL_DIR` | uv 装的 Python | `D:\software\python` | `~/.local/share/uv/python` | `~/.local/share/uv/python` |
| `TEMP` / `TMPDIR` | 临时 | `D:\tmp` | 系统默认，别改 | `/tmp` |

判据很简单：**macOS/Linux 上这些工具的默认值本来就落在该落的地方，不用设；Windows 的默认值在 C 盘用户目录，所以每一条都得显式改。** 在非 Windows 上照抄 Windows 的一整套 `export` 属于无用功，还会把缓存挪到不符合平台约定的位置。

## 6. Shell profile 落点

| 平台 / shell | 交互式配置 | 登录时配置（PATH、shellenv 放这儿） |
|---|---|---|
| Windows PowerShell 7 | `$PROFILE`（`~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`） | 同左 |
| Windows PowerShell 5.1 | `~\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` | 同左 |
| macOS zsh（默认 shell） | `~/.zshrc` | `~/.zprofile` |
| Linux bash | `~/.bashrc` | `~/.profile` |
| Linux/macOS zsh | `~/.zshrc` | `~/.zprofile` |

版本管理器的 init **必须**写进 profile，否则新终端里命令就找不到：

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$($(brew --prefix)/bin/brew shellenv)"     # macOS，写 ~/.zprofile
eval "$(fnm env --use-on-cd --shell zsh)"        # bash 改 --shell bash
```

```powershell
fnm env --use-on-cd | Out-String | Invoke-Expression
```

## 7. 明令禁止

**三平台通用**：不往需要提权的路径装开发依赖（发行版包管理器自己的地盘除外）；不手动解压二进制丢进 PATH。

| 平台 | 禁止 | 原因 |
|---|---|---|
| Windows | 软件与缓存落 C 盘 | 系统盘，重装即丢 |
| Windows | 不设 `PNPM_HOME`/`npm_config_prefix` 就 `npm i -g` | 全局包写进 `%APPDATA%`，跟着系统盘走 |
| macOS | `sudo brew ...` | Homebrew 会直接拒绝执行 |
| macOS | 改 `/usr/bin`、`/System` | SIP 保护，改不了也不该改 |
| macOS | 在 `/` 下新建顶层目录 | 只读系统卷 |
| macOS | 用系统 `/usr/bin/python3` 装包 | 那是 Xcode CLT 自带的，升级会被覆盖 |
| Linux | `sudo pip install` | PEP 668 起会被拒；绕过去会打坏发行版工具链 |
| Linux | `sudo npm i -g` | 同上，且全局包无法按用户隔离 |
| Linux | 手动往 `/usr/local/bin` 丢二进制 | 该进 `~/.local/bin` |
| WSL | 把代码或 node_modules 放 `/mnt/c`、`/mnt/d` | 跨文件系统访问，慢一个数量级。代码放 Linux 侧 `~/dev` |
| WSL | 复用 Windows 侧的二进制与路径 | WSL 里一律按 Linux 那列走 |

## 8. 排查「命令找不到」

按顺序走，别跳步：

| 步 | Windows | macOS / Linux |
|---|---|---|
| 1 装没装 | `Get-Command x` | `command -v x` |
| 2 它的 bin 在不在 PATH | `$env:PATH -split ';'` | `echo $PATH \| tr ':' '\n'` |
| 3 profile 加载了没 | `Test-Path $PROFILE`，开个新终端复现 | `exec $SHELL -l` 后重试 |
| 4 版本管理器 init 写进 profile 了没 | `$PROFILE` 里有没有 `fnm env` | rc 里有没有 `eval "$(fnm env)"` |
| 5 是不是装到别的 scope 了 | `scoop list` / `scoop which x` | `brew list` / `ls ~/.local/bin` |

九成落在第 3、4 步：**环境变量只对新开的终端生效**，或者版本管理器的 init 压根没写进 profile。

## 9. 平台细则

| 文件 | 内容 |
|---|---|
| `references/windows.md` | D 盘目录地图、Scoop 根目录、nvm-windows 存量说明、目录联接（junction） |
| `references/macos.md` | Homebrew 前缀与 cask、`~/Developer` 约定、`~/Library` 布局、Apple Silicon 注意事项 |
| `references/linux.md` | 各发行版包管理器对照、XDG 目录、PEP 668、Homebrew on Linux、WSL |
