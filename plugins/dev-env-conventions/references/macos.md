# macOS 细则

macOS 上**没有「装到另一个盘」这回事**，对应的诉求是「装到 `$HOME` 下，不写系统目录」。
系统卷自 Catalina 起是只读的签名卷（SIP 保护），所以 `/software` 这种顶层目录建不出来，也不该建。

## 目录约定

| 用途 | 路径 | 说明 |
|------|------|------|
| GUI 应用 | `/Applications` | `brew install --cask` 的默认落点；只给自己用的可放 `~/Applications` |
| Homebrew 前缀 | `/opt/homebrew`（Apple Silicon）/ `/usr/local`（Intel） | **用 `brew --prefix` 取，别硬编码** |
| 用户级可执行 | `~/.local/bin` | uv、pipx、自己写的脚本 |
| 代码仓库 | `~/Developer` | Apple 官方约定，Finder 里有专属图标 |
| 缓存 | `~/Library/Caches/<tool>` | npm、uv、pnpm 默认就落这儿 |
| GUI 应用数据 | `~/Library/Application Support/<app>` | |
| CLI 配置 | `~/.config/<tool>` | 命令行工具普遍走 XDG，不进 `~/Library` |
| 临时 | `$TMPDIR` | 系统给的 per-user 路径，**别改成 `/tmp`** |
| Agent 工作区 | `~/.agents` | |
| skills 仓库 | `~/Developer/skills` | |

## Xcode 命令行工具

装任何东西之前先装它，Homebrew 和大量 native 依赖（node-gyp、Python C 扩展）都要用：

```bash
xcode-select --install
xcode-select -p          # 确认路径
```

不需要装完整的 Xcode.app，除非做 iOS/macOS 原生开发。

## Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

装完必须把 shellenv 写进 `~/.zprofile`（Apple Silicon 上 `/opt/homebrew/bin` 不在默认 PATH 里）：

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

常用：

```bash
brew install git fnm uv         # CLI 工具
brew install --cask visual-studio-code   # GUI 应用，装进 /Applications
brew list          # 装了什么
brew --prefix fnm  # 某个包在哪
brew cleanup       # 清旧版本
```

**绝不 `sudo brew`** —— Homebrew 检测到会直接拒绝执行。它把整个前缀目录的属主设成当前用户，就是为了不需要 sudo。

## Apple Silicon 注意

| 项 | 说明 |
|---|---|
| brew 前缀 | `/opt/homebrew`（Intel 是 `/usr/local`）。两者可共存于同一台机器 |
| Rosetta | 只在需要跑 x86_64 二进制时装：`softwareupdate --install-rosetta` |
| 架构确认 | `uname -m` → `arm64`；`arch -x86_64 brew ...` 可强制走 Intel 那套 |
| Node | 装 arm64 原生版，别用 Rosetta 跑 x64 Node，性能差且 native 模块容易冲突 |

## Node / Python

```bash
brew install fnm
echo 'eval "$(fnm env --use-on-cd --shell zsh)"' >> ~/.zshrc
fnm install 22 && fnm use 22

brew install uv
uv python install 3.12
uv venv && uv add requests
uv tool install ruff          # 全局 CLI，落在 ~/.local/bin
```

**别用系统 `/usr/bin/python3`** 装包 —— 那是 Xcode CLT 自带的，系统升级会整个覆盖，且 `pip install` 会污染它。
同理 `/usr/bin/ruby`、`/usr/bin/perl` 也是系统托管的。

## shell profile

macOS 默认 shell 是 zsh：

| 文件 | 何时加载 | 放什么 |
|------|---------|--------|
| `~/.zprofile` | 登录 shell（新终端窗口） | PATH、`brew shellenv`、导出型环境变量 |
| `~/.zshrc` | 每个交互式 shell | 别名、补全、`fnm env`、提示符 |

改完 `exec $SHELL -l` 重载，或开新窗口。

## Gatekeeper

从网上下的、未签名的二进制第一次跑会被拦。确认来源可信后：

```bash
xattr -d com.apple.quarantine /path/to/binary
```

Homebrew 装的不受影响（它自己处理了）。这也是「优先用包管理器装」的一个理由。
