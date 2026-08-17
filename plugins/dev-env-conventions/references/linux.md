# Linux 细则

Linux 上「装到哪」由两套规范决定：**FHS**（系统级路径归 `/usr`，发行版包管理器管）和 **XDG Base Directory**（用户级东西归 `~/.local` / `~/.config` / `~/.cache`）。
不要造 `~/software` 这类自定义顶层目录 —— 工具的默认值本来就落在 XDG 路径上，改了反而要处处显式配。

## XDG 目录

| 变量 | 默认值 | 放什么 |
|------|--------|--------|
| `XDG_CONFIG_HOME` | `~/.config` | 配置文件 |
| `XDG_DATA_HOME` | `~/.local/share` | 程序数据（fnm 的 Node、uv 的 Python、pnpm 全局包） |
| `XDG_STATE_HOME` | `~/.local/state` | 日志、历史等可丢弃的状态 |
| `XDG_CACHE_HOME` | `~/.cache` | 缓存 |
| —（约定） | `~/.local/bin` | 用户级可执行，需自己加进 PATH |

`~/.local/bin` 不一定在默认 PATH 里（Debian 系的 `~/.profile` 会条件性加，但只在登录 shell 且目录已存在时）。稳妥做法是显式加：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## 发行版包管理器对照

| 发行版 | 更新索引 | 安装 | 搜索 | 已装列表 |
|--------|---------|------|------|---------|
| Debian / Ubuntu | `sudo apt update` | `sudo apt install -y <pkg>` | `apt search <kw>` | `apt list --installed` |
| Fedora / RHEL | `sudo dnf check-update` | `sudo dnf install -y <pkg>` | `dnf search <kw>` | `dnf list installed` |
| Arch | `sudo pacman -Sy` | `sudo pacman -S <pkg>` | `pacman -Ss <kw>` | `pacman -Q` |
| openSUSE | `sudo zypper refresh` | `sudo zypper install -y <pkg>` | `zypper search <kw>` | `zypper se -i` |
| Alpine | `sudo apk update` | `sudo apk add <pkg>` | `apk search <kw>` | `apk info` |

判定发行版：

```bash
. /etc/os-release && echo "$ID $VERSION_ID"   # ubuntu / debian / fedora / arch / alpine ...
```

编译类依赖（node-gyp、Python C 扩展都要）：

| 发行版 | 包 |
|--------|-----|
| Debian/Ubuntu | `build-essential python3-dev libssl-dev pkg-config` |
| Fedora | `@development-tools python3-devel openssl-devel` |
| Arch | `base-devel openssl` |
| Alpine | `build-base python3-dev openssl-dev` |

## Node

发行版仓库里的 Node 版本通常过旧，**不要** `apt install nodejs` 当主力。用 fnm：

```bash
curl -fsSL https://fnm.vercel.app/install | bash
# 写进 ~/.bashrc 或 ~/.zshrc
eval "$(fnm env --use-on-cd --shell bash)"

fnm install 22 && fnm use 22
corepack enable && corepack prepare pnpm@latest --activate
```

fnm 默认落在 `~/.local/share/fnm`，符合 XDG，不用改。

## Python

发行版自带的 Python 是**系统工具链的一部分**（`apt`、`dnf` 自己都用它），碰它会打坏系统。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12       # 装到 ~/.local/share/uv/python
uv venv && uv add requests
uv tool install ruff         # 全局 CLI，落到 ~/.local/bin
```

**`sudo pip install` 是禁止的**。自 PEP 668 起，发行版会把系统 Python 标记为 externally-managed，`pip install` 直接报错拒绝。看到这个报错时正确反应是**建 venv 或用 uv**，而不是加 `--break-system-packages` 绕过去 —— 那个参数的名字就是它的后果。

## Homebrew on Linux（可选）

需要跨发行版拿到一致的新版 CLI 时可以叠一层，前缀是 `/home/linuxbrew/.linuxbrew`：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

不是必需品。只在发行版仓库版本太旧、又不想逐个装二进制时才值得引入 —— 否则同一个工具装两份反而更乱。

## shell profile

| 文件 | 何时加载 | 放什么 |
|------|---------|--------|
| `~/.profile` | 登录 shell（含图形会话） | PATH、导出型环境变量 |
| `~/.bashrc` | 每个交互式 bash | 别名、补全、`fnm env` |
| `~/.zshrc` / `~/.zprofile` | zsh 对应上面两者 | 同上 |

注意 Debian 系的 `~/.bash_profile` 若存在会**取代** `~/.profile`，两个都写容易漏加载。统一往 `~/.profile` 放 PATH，`~/.bashrc` 放交互式配置。

## WSL

WSL 里**一律按 Linux 这一列走**，不要复用 Windows 侧的路径与二进制。

| 事项 | 做法 |
|------|------|
| 代码放哪 | Linux 侧 `~/dev`。**别放 `/mnt/c`、`/mnt/d`** —— 跨文件系统（9p）访问，`npm install`、`git status` 会慢一个数量级 |
| Node/Python | 在 WSL 里独立装一套，别调用 Windows 的 `node.exe` |
| PATH 污染 | WSL 默认把 Windows 的 PATH 追加进来，`which node` 可能指到 `/mnt/c/...`。查到了就在 `/etc/wsl.conf` 关掉 `appendWindowsPath = false` |
| 检测 | `grep -qi microsoft /proc/version` |
| 访问 Windows 文件 | 偶尔读写没问题；持续 IO 的目录不要放那边 |
