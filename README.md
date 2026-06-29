# longyi-skills

Longyi 的个人 Claude Code 技能市场（marketplace）。把仓库推到 GitHub 后，可在任意机器（自己电脑、公司电脑）上一行命令安装，无需手动拷贝文件。

## 当前收录的技能

| 插件 | 作用 |
|------|------|
| `project-onboarding` | 快速理解陌生代码仓库：缕清结构、技术栈、业务、目录职责与功能分块，给出「新功能落点指南」。适合新入职 / 接手新项目时使用。 |

## 一、首次发布（只需做一次）

把本目录初始化为 git 仓库并推到 GitHub（建议仓库名就叫 `longyi-skills`）：

```bash
cd longyi-skills
git init
git add .
git commit -m "init: longyi 个人技能市场"
git branch -M main
git remote add origin git@github.com:longyi-xw/longyi-skills.git
git push -u origin main
```

> 私有仓库也可以，只要安装时所在机器的 git 能访问该仓库即可（SSH key 或 token 配好）。

## 二、在任意机器上安装使用

在 Claude Code 会话里依次执行：

```bash
# 1. 添加你的市场（只需每台机器做一次）
/plugin marketplace add longyi-xw/longyi-skills

# 2. 安装技能
/plugin install project-onboarding@longyi-skills
```

安装时会让你选 **scope**：

- **User scope** → 装到 `~/.claude/skills/`，所有项目可用（推荐通用技能选这个）
- **Project scope** → 装到当前仓库 `.claude/skills/`，仅当前项目可用

`project-onboarding` 是通用工具，建议选 User scope。

安装后当前会话即可使用，无需重启。在任意陌生项目目录里说「帮我梳理下这个项目」「这项目新功能加哪」即可触发；也可显式点名让它用该技能。

## 三、更新技能

改完技能内容后，提交并推送：

```bash
git add . && git commit -m "update: xxx" && git push
```

各机器上刷新市场并重装即可拿到最新版（插件系统暂无自动更新）：

```bash
/plugin marketplace update longyi-skills
/plugin install project-onboarding@longyi-skills
```

## 四、以后添加新技能

本仓库可持续扩展。要新增一个技能（例如把你的 `study-notes` 也收进来）：

1. 在 `plugins/` 下新建一个文件夹，例如 `plugins/study-notes/`
2. 放入该技能的 `SKILL.md`（及其 `references/` 等资源）
3. 在 `plugins/study-notes/.claude-plugin/plugin.json` 写插件清单（可参照 `project-onboarding` 的）
4. 在根目录 `.claude-plugin/marketplace.json` 的 `plugins` 数组里追加一项
5. 提交推送

之后用 `/plugin install study-notes@longyi-skills` 即可安装。

## 目录结构

```
longyi-skills/
├── .claude-plugin/
│   └── marketplace.json          # 市场清单：列出所有插件
├── plugins/
│   └── project-onboarding/
│       ├── .claude-plugin/
│       │   └── plugin.json        # 插件清单
│       ├── SKILL.md               # 技能主体
│       └── references/            # 技能引用资源
│           ├── project-types.md
│           └── output-template.md
└── README.md
```
