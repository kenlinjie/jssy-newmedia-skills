# 全链路架构与数据契约

## 一句话

`monitor.py` 常驻轮询一批竞品抖音号（名单在 `watchlist.txt`） → 开播即录音频 → 下播自动转写 + 出数据报告 → `publish_prep.py` 聚合成静态站点 → 自动化发邮件 + 上线 → 第二天 08:50 跨场提炼情报。

程序目录：`<程序目录>`（下称 BASE）。除特别说明，所有命令都在 BASE 下执行。

## 分层图

```
【采集层】本地常驻，不依赖 WorkBuddy
  daemon.py ──拉起/看护──> monitor.py ──轮询──> 抖音直播接口（streamget）
                               │
                               ├─ status=2 开播 → ffmpeg 录音（600s/段，16k 单声道 FLAC）
                               ├─ shot.py 每段抓 1 帧 → frame_XXX.jpg / frame_open.jpg
                               ├─ 每分钟采样在线人数 → viewers.csv
                               └─ status≠2 下播 → 入 ASR 队列 → report.py → 报告.html + 摘要.md
                                                        → sync_all.py（站点 + 看板）
                                                        → 写 ENDED

【分发层】WorkBuddy 自动化，每 30 分钟
  主任务 ──读 _sessions.json──> 待发场次 → 写 复盘.md → 发邮件 → marker → sync_all → deploy
  兜底   ──读 watchdog.py───> 积压场次 → 同上（每 15 分钟错峰）

【提炼层】WorkBuddy 自动化，每天 08:50
  读昨天全部 transcript.txt → 写 <date>.intel.json → daily_intel.py → sync_all → deploy
```

## 目录与文件契约

### 每场直播目录

```
recordings/<抖音号>_<账号名>/<YYYY-MM-DD>/<HHMMSS>/
    meta.json           账号名、标题、room_id
    viewers.csv         在线人数采样曲线（列序见「坑」一节）
    audio_000.flac…     每段 600 秒
    frame_open.jpg      开播瞬间抓帧
    frame_XXX.jpg       每段结束抓帧
    cover.jpg           峰值时刻那一帧（下播时选定）
    transcript.txt      整场逐字稿（纯文本，无换行）
    transcript.srt      带时间戳逐字稿（report.py 提取话术依赖它）
    报告.html           数据报告（折线图、拐点）
    摘要.md             机器生成的摘要
    复盘.md             ★ 人/模型写的文字复盘，网站优先展示它
    share_link.txt      该场在线地址（含 sharecode）
    ENDED               下播标记（内容是目录路径）
    email_sent.marker   ★ 发信去重标记，存在即视为已发
```

### 站点

```
share/site/             ← publish_prep.py 生成（唯一生成源）
    index.html          报告中心：今日场次 / 本月账号汇总 / 按日全部场次，自有号置顶
    accounts.html       账号月度视图（一行一账号）
    analysis.html       分析大表（数字对比 + 打法拆解）
    kanban.html         看板（build_index.py 生成）
    daily/<date>.html   每日情报页
    reports/<key>/index.html
    shots/<key>.jpg
    _sessions.json      ★ 自动化的唯一数据源
share/online/           ← 每次 build 后整目录复制出的镜像，内容与 site 完全一致
share/base_url.txt      根域名
share/sharecode.txt     分享码
share/recipients.txt    竞品号收件人
share/recipients_self.txt  自有号收件人
share/self_rooms.txt    自有号白名单
```

### 每日情报

```
每日汇总/<date>.intel.json   情报内容（人/模型写）
每日汇总/<date>.html         daily_intel.py 渲染
每日汇总/<date>.md           同内容 Markdown，可直接贴群
```

## `_sessions.json` 字段（分发层唯一入口）

顶层：`base_url / count / old_count / pending_count / sessions[]`

每个 session：
`key / name / title / date / time / url / ended / email_sent / is_self / recipients / has_review / sdir`

- `pending_count` = `ended=true` 且 `email_sent=false` 的场次数。
- `recipients` 已按 `self_rooms.txt` 分好流，格式 `[{"email": "..."}]`。**发信只认这个字段，不要自己读配置文件。**

## `intel.json` 结构（提炼层产物）

```json
{
  "date": "2026-11-06",
  "headline": "一句话概括当天最重要的发现",
  "summary": "2-3 句摘要",
  "kpis": [["20", "场直播"], ["16", "个账号"], ["26h 38m", "总时长"],
           ["62", "单场峰值"], ["11928", "累计观看"], ["20", "封报告已发"]],
  "intel": [
    {"cat": "政策|对手动作|打法|数据|风险|自有号",
     "hot": true,
     "title": "有信息量的一句话",
     "body": "2-5 句，必须带具体数字或原话，写清谁在哪个时间点说的",
     "accounts": ["账号名"]}
  ],
  "chances": [["可以做的事标题", "1-2 句说明为什么、怎么做"]]
}
```

- `kpis` / `chances` 都是**二元组数组** `[值, 说明]`，不是对象。写错结构页面会空。
- `intel` 12-18 条，按重要性排序；`hot` 只给 4-6 条；`chances` 4-5 条。
- `cat` 只能取那六个值，其他值不会渲染样式。

## 脚本清单

| 脚本 | 作用 | 谁调用 |
|---|---|---|
| `monitor.py` | 主循环：轮询、录制、转写、收尾 | daemon / 自动化心跳 |
| `daemon.py` | 看护 monitor，崩溃 10 秒重启 | cli.py start |
| `cli.py` | 运维命令（start/stop/status/check/record/add/remove/list） | 人 |
| `asr.py` | 离线转写（sherpa-onnx + silero-vad） | monitor、recover_asr |
| `report.py` | 生成 报告.html + 摘要.md，下播收尾 | monitor |
| `shot.py` | 用同一拉流地址抓帧、选 cover | monitor |
| `publish_prep.py` | 扫 recordings → 建站点 + `_sessions.json` | sync_all、自动化 |
| `build_index.py` | 生成 看板.html | sync_all |
| `sync_all.py` | 三步顺序同步（见下） | monitor、digest、自动化 |
| `digest.py` | 按天汇总成 md/html | 手动或每日任务 |
| `daily_intel.py` | 读 intel.json → 渲染 html+md | 每日情报任务 |
| `watchdog.py` | 找「已下播未发信」的积压场次 | 兜底任务 |
| `solo_record.py` | 主监控在录别的号时，独立进程补录新号 | monitor |
| `recover_asr.py` | 批量补转写历史缺稿场次 | 人 |
| `idle_restart.py` | 空闲时重启监控，让改动生效 | 人 |
| `mdview.py` | 本地预览 md | 人 |

### `sync_all.py` 为什么必须整体跑

顺序敏感，拆开跑会导致看板里的链接是上一轮的：

1. `publish_prep.build_site()` → 复制报告进 site，写各场 `share_link.txt`
2. `build_index.build()` → 读上一步的 `share_link.txt` 生成看板
3. `publish_prep.build_site()` → 把刚生成的看板再同步进站点

## 数据流的关键不变式

1. **`email_sent.marker` 是唯一发信凭据**。存在即已发，任何任务都不得重发。
2. **`复盘.md` 与邮件正文必须逐字一致**。网站展示的就是邮件那一份。
3. **网站标签数字优先从 `复盘.md` 正文解析**，没有才回落 `摘要.md`，保证正文和标签不打架。
4. **`scan_daily()` 只认 `.html`**。只生成 `.md` 的日期在站点上等于不存在。
5. 站点部署幂等，重复部署只更新内容，根地址不变。
