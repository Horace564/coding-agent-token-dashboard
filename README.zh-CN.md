# Coding Agent Token Dashboard

[English](README.md) | [简体中文](README.zh-CN.md)

一个在本机查看 Claude Code 和 Codex token 用量的仪表盘。它读取电脑上已有的会话记录，帮助你按 prompt、模型调用、session、项目、缓存和 skill 查看 token 的去向。

运行只需要 Python 标准库和浏览器，无需账号、API Key、安装第三方包或构建前端。

## 功能

- **Overview（总览）：** token 总量与每日趋势、模型和项目对比，以及 Claude Code/Codex 工具使用统计表。
- **Prompts：** 按累计 token 或时间排列用户请求，查看每个请求包含的模型调用和缓存读取。
- **Sessions：** 查看有名称的会话，默认按累计 token 排序；每条 Prompt 显示 token 和工具调用次数，展开后可查看模型调用、可见的工具参数与结果，以及 Codex 上下文压缩事件。
- **Skills：** 统计 Claude Code 的 `Skill` 调用，并根据 Codex 读取 `SKILL.md` 的记录推断 skill 使用次数。

顶部的来源选择器可以切换 Claude Code、Codex 或全部数据。

## 运行要求

- Python 3.10 或更新版本
- 现代浏览器
- 至少一份本地 Claude Code 或 Codex 会话记录

## 快速开始

```bash
git clone https://github.com/Horace564/coding-agent-token-dashboard.git
cd coding-agent-token-dashboard
python3 cli.py dashboard
```

Windows 如果没有 `python3` 命令，可使用 `py -3 cli.py dashboard`。

启动命令会扫描本地会话，在 `http://127.0.0.1:8080` 启动服务并打开浏览器。程序每 30 秒检查一次新记录；按 `Ctrl+C` 停止。

## 数据来源与 token 口径

| 来源 | 默认会话目录 | 可查看的信息 |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/` | Prompt、每次响应的用量、工具调用和 skill 调用 |
| Codex | `$CODEX_HOME/sessions` 或 `~/.codex/sessions` | Prompt、每次响应的用量、可见的助手与工具活动、压缩事件和推断的 skill 使用 |

扫描只读取原始会话文件，不会修改它们。仪表盘在 `~/.claude/token-dashboard.db` 保存自己的 SQLite 缓存。Codex 工具参数和结果在缓存中各保留最多 12,000 个字符的预览。

**Total tokens** 是多次模型调用的累计用量，包含重复读取的缓存 token；它不是单次调用的上下文窗口大小。Fresh input、output、cache read 和 cache write 列展示其组成。

仪表盘只统计 token 用量，不估算美元费用。Codex 的 skill 统计依据记录中的 `SKILL.md` 读取命令推断：同一用户 turn 对同一 skill 最多计一次。“skill 文件 token 数”只是文件大小估算，并非实际消耗。

Codex 的本地 rollout 格式可能变化。本地扫描不包含仅存于云端或其他设备的会话。其他边界见[已知限制](docs/KNOWN_LIMITATIONS.md)。

## 命令

```bash
python3 cli.py scan       # 更新 SQLite 缓存后退出
python3 cli.py today      # 查看今天的 token 总量
python3 cli.py stats      # 查看累计 token 总量
python3 cli.py dashboard  # 扫描并打开仪表盘

python3 cli.py dashboard --no-open
python3 cli.py dashboard --no-scan
python3 cli.py dashboard --rebuild-db  # 根据当前 JSONL 重建缓存
python3 cli.py dashboard --reload    # Python 代码修改后自动重启后端
```

`--rebuild-db` 会先生成新的 SQLite 缓存，两个来源扫描成功后才替换旧库。已删除或移出扫描目录的 JSONL 对应的会话将从仪表盘消失；原始会话文件不会被修改。重建前请关闭使用同一数据库的其他 Dashboard。此参数不能与 `--no-scan` 同时使用。

Windows 可将 `python3` 换成 `py -3`。

## 配置

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | 服务绑定地址 |
| `PORT` | `8080` | 服务端口 |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Claude Code 会话目录 |
| `CODEX_HOME` | `~/.codex` | Codex 本地状态目录 |
| `CODEX_SESSIONS_DIR` | `$CODEX_HOME/sessions` | 单独指定 Codex 会话目录 |
| `TOKEN_DASHBOARD_DB` | `~/.claude/token-dashboard.db` | SQLite 缓存位置 |

命令行也支持 `--projects-dir`、`--codex-dir` 和 `--db`。例如：

```bash
python3 cli.py dashboard --projects-dir /path/to/claude/projects --codex-dir /path/to/codex/sessions --db /path/to/cache.db
```

若只希望本机访问会话记录，请将 `HOST` 保持为 `127.0.0.1`。在仪表盘按 `Ctrl+B` 或 `Cmd+B` 可模糊敏感文本，方便截图。

## 开发

```bash
python3 -m unittest discover tests
```

后端使用 Python 标准库和 SQLite；前端使用原生 JavaScript 和项目内置的 ECharts。开发约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

开发时使用 `python3 cli.py dashboard --reload`。它每秒检查一次 Python 源码，修改后自动重启后端；已打开的仪表盘页面会在服务重新连接后刷新。原有的每 30 秒 JSONL 扫描照常运行。若同时使用 `--rebuild-db`，只在首次启动时重建缓存。按 `Ctrl+C` 停止监听。

## 致谢

本项目 fork 自 Nathan Herkelman 的 [nateherkai/token-dashboard](https://github.com/nateherkai/token-dashboard)。当前版本加入了 Codex 支持，并扩展了面向两种编程代理的会话与用量视图。

## 许可证

[MIT](LICENSE)。
