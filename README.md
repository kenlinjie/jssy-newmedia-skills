# 新东方省域新媒体技能包

本项目包含 **20 个通用技能**，覆盖 AI 工作环境、公众号、直播后台填表、公开抖音对标、视频处理、日报、培训汇报、笔记管理和钉钉协作。只提供通用流程、公开参考和空白模板。

## 固定下载入口

[国内镜像下载 · 主分支](https://gh-proxy.org/https://github.com/kenlinjie/xdf-province-new-media-skills/archive/refs/heads/main.zip)

这个地址始终指向主分支，后续更新沿用同一入口。解压完整项目后按下方说明使用。镜像由第三方运营，服务可用性与缓存刷新由服务方决定。

备用入口：[GitHub 原始下载](https://github.com/kenlinjie/xdf-province-new-media-skills/archive/refs/heads/main.zip)；[项目仓库](https://github.com/kenlinjie/xdf-province-new-media-skills)。

## 怎么使用

把项目目录交给已有的 WorkBuddy、Claude Code、Codex 或其他可读技能的 agent：

> 请先读 AGENTS.md，按省域新媒体工作入口帮我完成这项任务：……

已有明确技能时，直接读取 `skills/技能名/SKILL.md`。安装与首次使用步骤见 [同事上手](docs/同事上手.md)。

## 按工作找技能

| 场景 | 技能 |
| --- | --- |
| 省域新媒体综合工作入口 | [xdf-province-new-media](skills/xdf-province-new-media/SKILL.md) |
| AI环境配置 | [ai-environment-setup](skills/ai-environment-setup/SKILL.md) |
| 公众号写稿与排版 | [gzh-design](skills/gzh-design/SKILL.md) |
| 团队通用日报 | [daily-report-universal](skills/daily-report-universal/SKILL.md) |
| 公开抖音账号对标 | [douyin-benchmark](skills/douyin-benchmark/SKILL.md) |
| 直播后台数据填表 | [live-backend-to-sheet](skills/live-backend-to-sheet/SKILL.md) |
| 文案修改与去AI腔 | [write](skills/write/SKILL.md) |
| 文风与口播长期学习 | [voice-loop](skills/voice-loop/SKILL.md) |
| 看视频与按时间点复盘 | [watch](skills/watch/SKILL.md) |
| 本地中文音视频转写 | [local-sota-transcription](skills/local-sota-transcription/SKILL.md) |
| 口播视频剪辑与包装 | [remotion-talking-head](skills/remotion-talking-head/SKILL.md) |
| 网页演示与培训分享 | [guizang-ppt-skill](skills/guizang-ppt-skill/SKILL.md) |
| 可编辑PPT与PPTD项目 | [open-kimi-ppt](skills/open-kimi-ppt/SKILL.md) |
| SVG转可编辑PPT | [ppt-master](skills/ppt-master/SKILL.md) |
| 联网检索与平台资料读取 | [agent-reach](skills/agent-reach/SKILL.md) |
| 网页正文转Markdown | [defuddle](skills/defuddle/SKILL.md) |
| Obsidian笔记操作 | [obsidian-cli](skills/obsidian-cli/SKILL.md) |
| Obsidian笔记格式 | [obsidian-markdown](skills/obsidian-markdown/SKILL.md) |
| Obsidian数据视图 | [obsidian-bases](skills/obsidian-bases/SKILL.md) |
| Obsidian思维画布 | [json-canvas](skills/json-canvas/SKILL.md) |
| 钉钉消息、文档、AI 表格、日历等 | [钉钉 CLI 官方站](https://open.dingtalk.com/dingtalk-cli)（外部工具） |

## 安装与打包

需要 Python 3.9+。安装器只复制随附技能，不安装软件、不登录账号，已有同名技能会保留。钉钉相关直接使用[官方 CLI 站点](https://open.dingtalk.com/dingtalk-cli)提供的安装、授权与官方技能；本项目不再随附钉钉产品技能副本。

```bash
python3 scripts/skillpack.py list --profile core
python3 scripts/skillpack.py check
python3 scripts/privacy_check.py
python3 scripts/skillpack.py install --target workbuddy --profile core
python3 scripts/skillpack.py install --target workbuddy --profile core --apply
python3 scripts/skillpack.py package
```

`core` 是 8 个常用技能，`team` 是全部 20 个随附技能。`--target` 可选 `agents`、`codex`、`claude`、`workbuddy`；`--skill` 可指定单个技能，所需技能依赖会一并选择。安装后新开或重载 agent 会话。

日常下载直接使用上面的固定入口，无需等待单独的安装包。需要自行分发时可运行打包命令，生成的文件保存在本地 `dist/`，不会自动上传。

## 直播后台填表怎么用

老师可以直接说：

> 帮我把这周的直播后台数据填到表里，先带我确定用哪个直播号、有没有登录，以及填哪张表。

`live-backend-to-sheet` 会用 ego Lite 检查真实登录状态，再引导确定目标表链接或 Excel 文件、直播周期。字段默认按老师提供的表头，能确定的先填，不确定的留空或保留原值；填后用大白话指出哪场、哪列拿不准，主动问老师后续怎么处理。扫码、切号或授权由老师在官方界面完成；填写后读回核对，重跑先查重，已明确的任务信息直接沿用。

浏览器从 [ego Lite 官网](https://www.egolite.ai/download)按当前说明安装，操作前读取 `ego-browser skill`。目标是钉钉表时使用 `dws`，其他在线表使用可见编辑界面，本地 Excel 在后台处理。账号、表链接和执行记录保存在使用者自己的项目外目录。

## 共享内容与个人状态

业务材料、历史日报、文风语料和个人配置由各使用者保存在本项目外。模板保持空白，业务目标和账号权限以当次任务为准。项目说明、技能正文、样例和分发包都不引用私人库名或个人设备信息。

打包前检查项目，再检查生成的 ZIP。隐私检查只报告规则与文件位置，不输出命中的敏感内容；发现问题即停止，不覆盖此前成功生成的安装包。

文件完整性检查和试装不代表已经连通办公账号或执行真实业务。软件、模型、登录和组织权限在使用相应技能时核验。

## 来源与维护

公开来源、许可文件、依赖和整合适配见 [catalog.json](catalog.json) 与 [许可说明](THIRD_PARTY.md)。保留各技能必要的公开署名和许可。更新技能后复核正文和资源，再更新哈希并运行检查。

项目同步到 [GitHub 仓库](https://github.com/kenlinjie/xdf-province-new-media-skills)，只维护通用技能、公开参考和空白模板。后续更新先执行检查，再提交并推送 `main` 分支。
