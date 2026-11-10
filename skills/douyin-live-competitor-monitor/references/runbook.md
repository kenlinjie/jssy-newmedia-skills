# 运维手册（按场景查）

所有命令默认在 `<程序目录>` 下执行。Python 用系统 `python`，若报找不到模块用
`<Python路径>`。

## 0. 任何操作之前：先体检

```bash
python <技能目录>\scripts\healthcheck.py
```

一次输出：监控是否活着、在录哪几个号、有没有漏发积压、站点待发数、磁盘、模型、今日场次进度、日志报错。
**先看结论行**，`OK` 就不要乱动；`ATTENTION` 按 blockers 逐条处理。

---

## 1. 查看现状

| 想知道 | 命令 |
|---|---|
| 监控进程状态 + 每个号在播/在录 | `python cli.py status` |
| 监控名单（若干号） | `python cli.py list` |
| 单个号此刻是否开播、在线人数、拉流地址 | `python cli.py check <抖音号>` |
| 有没有漏发 | `python watchdog.py --json` |
| 站点待发场次 | `python publish_prep.py` 后看 `share/site/_sessions.json` 的 `pending_count` |

`cli.py status` 有两种"活着"的判定：`daemon.pid` 进程在 （计划任务启动），或 `state.json` 5 分钟内更新过（主进程直跑）。二者任一成立即在跑。

---

## 2. 启动 / 停止 / 重启

```bash
python cli.py start      # 后台拉起 daemon（崩溃 10s 自动重启）
python cli.py stop       # 停止守护与监控，清理 pid
python cli.py status     # 确认
```

**重启的两个前提**（写死，别忘）：

- 有场次正在录制时**不要重启**，会截断该场录音、报告不完整。先 `cli.py status` 看有没有「●直播录制中」。
- 改了 `monitor.py` / `asr.py` / `report.py` / `shot.py` 后，必须先 `python -m py_compile <文件>`，再重启才生效。

空闲时想安全重启，用 `python idle_restart.py`：它会等所有场次收尾完再重启。

---

## 3. 增删监控号

```bash
python cli.py add <抖音号> [账号名]     # 写入 watchlist.txt
python cli.py remove <抖音号>
python cli.py list
```

抖音号取自 `https://live.douyin.com/<这段>`，纯数字或自定义号都行。
**改完不需要重启监控**，主循环每轮重读 `watchlist.txt`。

## 4. 改收件人

| 改什么 | 改哪个文件 |
|---|---|
| 竞品报告收件人 | `share/recipients.txt` |
| 自有号报告收件人 | `share/recipients_self.txt` |
| 哪些号算"自有号" | `share/self_rooms.txt` |

每行一个，`#` 开头是注释。改完下一封自动生效，**不需要重启、不需要动自动化**。
自有号命中白名单后：邮件主题变 `[自有号复盘]`，正文第五节变「下次必须改的三点」，且只发 `recipients_self.txt`。

---

## 5. 场景：某场下播了但没收到邮件

**先判断是"还没轮到"还是"真漏了"**：

```bash
python watchdog.py            # 人看的版本，会列出积压场次和已下播多少分钟
```

- `积压 0 场 / 宽限期内 N 场` → 正常。宽限期 15 分钟是留给主任务的处理窗口，等下一轮即可。
- `积压 > 0` → 真漏了。按兜底任务标准处理（见 `automations.md` 的兜底任务）：读 `摘要.md` + `transcript.txt` → 写 `复盘.md` → 发邮件 → **确认已发送** → 写 `email_sent.marker` → `sync_all.py` → 部署 → `build_index.py`。

不要因为"想确认一下"就重发。**marker 存在即视为已发。**

---

## 6. 场景：手动补一场的复盘（已下播、有报告、没发信）

```bash
python watchdog.py --grace 0      # 宽限期归零，刚下播的也列出来
```

拿到 `sdir_abs` 后：

1. 读 `摘要.md`、`viewers.csv`、`transcript.txt`（大文件分段读完，别只读开头）
2. 按六节结构写 `复盘.md`，存到 `sdir_abs\复盘.md`
3. 发邮件（主题 `[竞品复盘] <主播> · <日期>`），正文 = 复盘正文 + 分隔线 + 在线链接
4. 确认出现在「已发送」后写 `email_sent.marker`
5. `python sync_all.py` → 部署 `share\site` → `python build_index.py`

六节结构、写作标准见 `review-template.md`。

---

## 7. 场景：补转写（有音频没逐字稿）

典型症状：报告里「话术/内容要点」全显示"未检测"。

先单段试：

```bash
python asr.py <某个.flac 路径>
```

批量补某个目录：

```bash
python recover_asr.py          # 看它的参数说明，默认扫 recordings 下缺 transcript.txt 的场次
python report.py <场次目录>     # 补完重跑报告
```

ASR 大约 **4x 实时**，一段 600 秒音频要 2-3 分钟。若干号晚间撞场时报告会排队几分钟，**这是正常的，不是卡住**。

---

## 8. 场景：站点/看板内容不对

```bash
python sync_all.py        # 三步顺序同步，别拆开
```

同步完在本地打开 `看板.html` 或 `share/site/index.html` 核对。
确认无误后部署：

```
workbuddy_sites_deploy
  action=deploy
  directory=<程序目录>\share\site
  language=static
  appName=竞品直播复盘报告中心
  domainPrefix=<站点域名前缀>
  userAskedToPublish=true
```

根地址固定 `<报告站根地址>`。
**所有子页面链接必须带 `?sharecode=<share/sharecode.txt>`**，否则报"链接不完整"。链接一律由脚本生成，不要手写。

---

## 9. 场景：生成某天的人工汇总

```bash
python digest.py 2026-11-06      # 缺省=昨天，产出 每日汇总/<date>.md + .html
```

注意 `digest.py` 是按场罗列的**流水账**，决策价值低；真正有价值的是 `daily_intel.py` 那份跨场提炼的情报。日常只需跑情报，`digest` 仅在需要按场清单时用。

## 10. 场景：重渲染某天的情报页

```bash
python daily_intel.py 2026-11-06   # 读 <date>.intel.json → 重出 html + md
python sync_all.py
```

改完 `.intel.json` 后必须重跑这一步，否则站点还是旧版。

---

## 11. 日常节奏（不用人管，知道就行）

| 时间 | 谁 | 干什么 |
|---|---|---|
| 每 180 秒 | monitor.py | 轮询 若干号 |
| 每 60 秒 | monitor.py | 采样在线人数 |
| 实时 | monitor.py | 开播录音、下播出报告、同步站点 |
| 每小时 0/30 分 | 主任务自动化 | 写复盘 + 发邮件 + 上线 |
| 每小时 5/20/35/50 分 | 兜底自动化 | 找积压补发 |
| 每小时整点 | 心跳自动化 | state.json 超 15 分钟没更新就重新拉起 monitor |
| 每天 08:50 | 情报自动化 | 读昨天逐字稿 → 出情报页 → 上线 |

## 12. 日志与现场

| 文件 | 看什么 |
|---|---|
| `logs/monitor.log` | 主流程日志，报错保留现场，**先看这里** |
| `logs/daemon.out` | daemon 的 stdout/stderr |
| `state.json` | 最近一轮轮询结果（`updated` 超过 5 分钟=可能停摆） |
| `monitor.pid` / `daemon.pid` | 进程号 |

查报错：

```bash
grep -n -E "Traceback|\[错误\]|\[失败\]" logs/monitor.log | tail -20
```
