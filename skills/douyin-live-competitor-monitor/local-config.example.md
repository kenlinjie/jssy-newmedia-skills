# 本机配置（空白模板）

安装时本文件被复制为 `local-config.md`。把自己机器上的真实值填进去，只留在本机，不要提交到共享仓库或分发包。

SKILL.md 与 `references/` 里的占位符一律按下表取值：

| 占位符 | 说明 | 填法 |
| --- | --- | --- |
| `<程序目录>` | 监控系统程序目录（含 `monitor.py`、`cli.py`、`share/`、`recordings/`） | 例：`D:\monitor`，本机实际路径 |
| `<Python路径>` | 跑这套系统的 Python 解释器 | 优先系统 `python`；找不到模块时填解释器全路径 |
| `<技能目录>` | 本技能所在目录 | 安装目标下的 `douyin-live-competitor-monitor` |
| `<报告站根地址>` | 部署后的站点根地址 | 由部署平台给出，如 `https://<你的域名前缀>.app.workbuddy.host` |
| `<站点域名前缀>` | 部署时的 `domainPrefix` | 与根地址一致，所有任务统一用一个前缀 |
| `<分享码>` | 站点访问分享码 | 存 `share/sharecode.txt`，子页面链接必须带 `?sharecode=` |
| `<自有号收件人>` | 自有号复盘的收件人邮箱 | 用团队实际邮箱，不要抄送同事 |

## 配置文件位置（都在程序目录的 `share/` 下）

| 文件 | 内容 |
| --- | --- |
| `share/base_url.txt` | 站点根地址 |
| `share/sharecode.txt` | 分享码 |
| `share/recipients.txt` | 竞品号场次收件人，每行一个邮箱 |
| `share/recipients_self.txt` | 自有号场次收件人 |
| `share/self_rooms.txt` | 自有号白名单，决定分流 |
| `watchlist.txt` | 监控名单，格式 `抖音号  # 账号名` |

改这几个 txt 不需要重启监控，下一轮轮询生效。
