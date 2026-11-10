---
name: douyin-live-competitor-monitor
description: 运维「本地竞品抖音直播间 24 小时自动监控」系统：查看监控状态与在播场次、排查漏发、增删竞品号、补转写与补发复盘邮件、生成跨场每日情报、部署在线报告站点、迁移到新机器。当用户提到竞品直播、竞品监控、直播复盘、复盘.md、每日情报、看板、报告中心、漏发、watchdog、监控没跑、加竞品号、竞品直播间等，或要求查看/修复/重建这套 24h 自动化链路时使用。This skill should be used when the user asks about competitor livestream monitoring, live session review reports, daily intelligence digests, or the 24/7 Douyin monitoring pipeline deployed on the user's own machine.
agent_created: true
---

# 竞品直播间 24h 监控与情报

## 先读本机配置

本技能只固化操作口径，具体路径、站点地址、分享码和收件人由使用者在 `local-config.md` 里填（安装时从 `local-config.example.md` 复制生成）。正文里的 `<程序目录>`、`<Python路径>`、`<技能目录>`、`<报告站根地址>`、`<站点域名前缀>`、`<分享码>`、`<自有号收件人>` 一律按该文件取值；没有这份文件就先照着示例问清再动手，不要猜。

## Overview

`<程序目录>` 下已部署一套完整系统：常驻轮询若干个本地竞品抖音号 → 开播自动录音频 → 下播转写并出数据报告 → 聚合成可分享的在线报告中心 → 每场复盘自动发邮件 → 每天 08:50 跨场提炼情报上线。

本 skill **不重新实现采集代码**，而是把这套系统的操作口径、数据契约、内容标准与踩坑经验固化下来，使任何一次会话都能正确运维、产出、排查和迁移，而不是每次重新读 20 个 py 文件猜行为。

## 何时使用

- 问"监控在跑吗""今天几个号开播""谁在录"
- 收不到报告邮件、怀疑漏发、要补发某场
- 加/减竞品号、改收件人、改自有号白名单
- 要写或重做某场 `复盘.md`、要出某天的每日情报
- 站点/看板内容不对、报告链接打不开、要重新部署
- 想把整套系统搬到另一台机器，或重建自动化任务

## 硬性规则（任何场景都不得违反）

1. **不编造数据**：在线人数、话术、政策数字只取接口与逐字稿，拿不到一律写「未获取」，绝不估算。
2. **不改合规红线**：不开浏览器、不登录、代码不写 Cookie；只录音频，不录视频、不抓弹幕；未经确认不向外发消息。
3. **`email_sent.marker` 是唯一发信凭据**：存在即视为已发，任何理由都不重发。
4. **有场次正在录制时不重启监控**：先确认无「●直播录制中」，用 `idle_restart.py` 等空闲。
5. **不拆开跑 `sync_all.py`**：三步顺序敏感，拆开会得到旧链接的看板。
6. **`复盘.md` 与邮件正文逐字一致**：网站展示的就是邮件那一份。
7. 改 `monitor.py` / `asr.py` / `report.py` 后先 `python -m py_compile` 再重启。

## 第一步：永远先体检

```bash
python <技能目录>\scripts\healthcheck.py
```

只读脚本，一次给出：监控是否活着、正在录哪几个号、漏发积压、站点待发、磁盘、模型、今日场次进度、日志报错。
加 `--json` 拿结构化结果；换机器用 `--base <路径>` 或环境变量 `DLM_BASE`。

结论 `OK` 就不要动系统；`ATTENTION` 按 blockers 逐条处理。**不要跳过体检直接重启或重发。**

## 场景路由

| 用户要什么 | 读哪份 | 关键动作 |
|---|---|---|
| 查状态 / 查漏发 | `references/runbook.md` §0-1 | `healthcheck.py` → `cli.py status` → `watchdog.py` |
| 启停重启 / 增删号 / 改收件人 | `references/runbook.md` §2-4 | `cli.py start\|stop\|add\|remove`；改 3 个 txt 无需重启 |
| 补发某场 / 手动写复盘 | `references/runbook.md` §5-6 + `references/review-template.md` | 写 `复盘.md` → 发信 → 确认已发送 → marker → `sync_all.py` → 部署 |
| 补转写 | `references/runbook.md` §7 | `asr.py` → `recover_asr.py` → `report.py` |
| 站点/看板不对 | `references/runbook.md` §8 | `sync_all.py` → 部署 `share\site` |
| 出每日情报 | `references/analysis-playbook.md` + `references/architecture.md` | 切稿 → 分层读 → grep 抽检 → `.intel.json` → `daily_intel.py` → `sync_all.py` → 部署 → WebFetch 核对 |
| 自动化没跑 / 要重建 | `references/automations.md` | 核对 4 个 ACTIVE 任务；#5 保持 PAUSED |
| 搬到新机器 | `references/deploy.md` | 装依赖与模型 → 改 `launch.bat` → 管理员注册计划任务 → 重建自动化 |
| 报错 / 数据对不上 / 链接打不开 | `references/pitfalls.md` | 按表排查 |

## 命令速查（均在 `<程序目录>` 下）

```bash
python cli.py status|start|stop|list|check <号>|add <号> [名]|remove <号>
python watchdog.py --json              # 漏发积压（--grace 0 取消宽限）
python sync_all.py                     # 站点 + 看板三步同步，顺序敏感
python build_index.py                  # 只刷看板（一般交给 sync_all）
python digest.py [YYYY-MM-DD]          # 按场流水账汇总，缺省=昨天
python daily_intel.py [YYYY-MM-DD]     # 读 .intel.json 渲染情报 html+md
python recover_asr.py                  # 批量补转写
python publish_prep.py --check         # 仅检查有无新场次/待发（exit 0=有）
```

日志：`logs/monitor.log`（先看这里）、`logs/daemon.out`。

## 关键事实（别再重新找）

- 程序目录 `<程序目录>`；监控名单 `watchlist.txt`（若干号，格式 `抖音号  # 账号名`）。
- 场次目录 `recordings/<号>_<名>/<日期>/<HHMMSS>/`，核心文件见 `references/architecture.md`。
- 站点生成源 `share/site/`，`share/online/` 是自动镜像；部署目录用 `share/site`。
- 根地址 `<报告站根地址>`，**所有子页面链接必须带 `?sharecode=<码>`**（码在 `share/sharecode.txt`），否则报"链接不完整"。
- 收件人分流由 `publish_prep.py` 按 `share/self_rooms.txt` 完成，写进 `_sessions.json` 的 `recipients`；发信**只认这个字段**，不要自行读配置或增减收件人。竞品号按 `share/recipients.txt` 逐个发，自有号只发给 `<自有号收件人>`。
- 站点三个入口：`index.html` 报告中心 / `accounts.html` 账号月度 / `analysis.html` 分析大表；另有 `kanban.html` 看板。
- 每日情报产物：`每日汇总/<date>.intel.json` + `.html` + `.md`。`scan_daily()` **只认 `.html`**，只出 md 站点不显示。
- 发信去重靠 `email_sent.marker`；主任务 0/30 分，兜底 5/20/35/50 分，情报 08:50，心跳每小时。
- 抖音无直播回放接口，2026-10-30 之前只录音频的场次无法补画面，属预期。

## 内容生产的最低标准

写 `复盘.md`：六节固定结构（整场数据 / 走势 / 内容与卖点 / 引导话术与转化 / 启示 / 合规说明），第三节必须带原话或具体数字，第四节没有留资动作就直接点破「零表单、零二维码、零商品、零价格」。详见 `references/review-template.md` 的好稿/差稿对照。

写每日情报：**跨场主题 + 多号口径冲突**才叫情报，逐场罗列是废稿。逐字稿必须先按标点切 240-260 字/行，主代理亲读 2-4 个高价值场次（数据型头部号、政策解读型账号优先），其余交子代理并行摘录，并要求额外产出「口径疑点」「同一账号上下半场冲突」两节；所有关键数字 grep 回原文抽检后再落笔。详见 `references/analysis-playbook.md`。

## References 索引

| 文件 | 何时读 |
|---|---|
| `references/architecture.md` | 需要理解全链路、目录契约、`_sessions.json` / `intel.json` 字段、脚本职责 |
| `references/runbook.md` | 任何具体操作前查命令与前置条件 |
| `references/review-template.md` | 写或改某场复盘前 |
| `references/analysis-playbook.md` | 出每日情报前（必读） |
| `references/automations.md` | 自动化失效、要重建、要改调度 |
| `references/pitfalls.md` | 报错、数字对不上、链接打不开、页面空白 |
| `references/deploy.md` | 迁移到新机器 / 从零部署 |
| `local-config.md` | 第一次使用先读：本机程序目录、站点地址、分享码、收件人 |
| `scripts/healthcheck.py` | 每次开始工作第一个执行 |
