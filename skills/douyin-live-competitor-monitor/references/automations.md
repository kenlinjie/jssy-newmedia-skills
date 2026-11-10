# 自动化任务配置（可重建清单）

系统 24 小时无人值守靠 **4 个 ACTIVE 自动化 + 2 个 Windows 计划任务**，不是靠对话里手动起的进程。
以下配置读自 2026-11-07 的实况，用 `automation_update` 工具（`mode=create` / `update`）重建。

## 总表

| # | 名称 | ID | 频率 | 状态 | 作用 |
|---|---|---|---|---|---|
| 1 | 竞品直播报告：发邮件+上线分享链接+刷新看板 | `5f985aff-5064-4a00-9d60-f7ac343320f6` | `FREQ=HOURLY;INTERVAL=1;BYMINUTE=0,30` | ACTIVE | **主推送** |
| 2 | 竞品直播漏发兜底 | `fd6cbe3f-5741-4d3f-8082-5497b3fee0f5` | `FREQ=HOURLY;INTERVAL=1;BYMINUTE=5,20,35,50` | ACTIVE | 错峰补发 |
| 3 | 每日竞品情报 | `5a3a4392-9eea-402e-a99c-3247539d3e81` | `FREQ=DAILY;BYHOUR=8;BYMINUTE=50` | ACTIVE | 跨场提炼上线 |
| 4 | 竞品监控心跳保活 | `863acbda-5ebc-4d0c-90dc-6deaa854b990` | `FREQ=HOURLY;INTERVAL=1` | ACTIVE | 会话期保活 |
| 5 | 竞品直播间每日汇总推送 | `8c852fc4-af77-42a9-a9fd-2ae38bd8cdc7` | `FREQ=DAILY;BYHOUR=9;BYMINUTE=5` | **PAUSED** | 已被 #3 取代，别启用 |

- 所有任务 `cwds` 均为 `<程序目录>`（#4 是 `<程序目录>`）。
- 主任务与兜底任务**靠 `email_sent.marker` 互斥**，谁先跑谁发，不会重复。
- 为什么要有兜底：主任务在 WorkBuddy 会话活跃时会被推迟，已实际造成两次漏发（16:01 下播拖到 16:37、16:39 下播无人处理）。内容链路没问题，问题在触发可靠性。

## Windows 计划任务（真正的 24h 底座）

| 任务名 | XML | 作用 |
|---|---|---|
| `竞品直播间监控` | `install_task.xml` | 开机自启 `launch.bat`，SYSTEM 账户（S-1-5-18），不登录也跑 |
| `竞品直播间每日汇总` | `digest_task.xml` | 每天 09:00 跑 `digest.py` |

注册：右键 `install_tasks.bat` → **以管理员身份运行**（双击不会 UAC 提权，会失败）。
校验：`schtasks /Query /TN "竞品直播间监控"` 状态 `Ready`。

心跳自动化 #4 只是 WorkBuddy 会话期的补充，**不能替代**这两个计划任务。

---

## #1 主推送（0 分 / 30 分）

```
竞品直播报告自动推送（幂等任务，可重复执行，重复执行不会重复发信）。
工作目录：<程序目录>

【步骤 1】执行 `python publish_prep.py`。
  扫描 recordings/ 下所有已生成 报告.html 的场次，同步到 share/site/，写出 share/site/_sessions.json。
  _sessions.json 字段：base_url、count、pending_count、sessions 数组；
  每个 session 含 key/name/title/date/time/url/ended/email_sent/is_self/recipients/has_review/sdir。

【步骤 2】读取 share/site/_sessions.json。
  pending_count == 0 → 直接结束，不发邮件、不部署、不做任何操作。
  pending_count > 0  → 继续。

【步骤 3】对每个 pending 场次（ended=true 且 email_sent=false）逐场处理：
 a. 打开 sdir，读 摘要.md 和 transcript.txt（大文件时分段读完），提炼内容。
 b. 写复盘正文（Markdown 中文），六节结构见 review-template.md：
    # 竞品直播复盘｜<主播名>（is_self=true 时「# 自有号直播复盘｜…」）
    **主播** / **场次** / **标题** 一行
    一、整场数据（表格：峰值在线/平均在线/累计观看/开播收尾在线）
    二、在线人数走势（时序 + 一句结论：稳定上扬/推流突发/一路下滑/窄幅波动）
    三、核心内容与卖点（3-6 条，来自逐字稿真实内容，带原话或具体数字）
    四、引导话术与转化动作（真实原话；转化漏斗；没有留资动作要直接指出）
    五、对我们的启示（2-3 条；is_self=true 改为「下次必须改的三点」）
    六、合规说明（固定文案）
    严禁编造，拿不到写「未获取」；不写在线链接、不写本地路径、不用 emoji、不写 HTML。
 c. 正文原样保存为 <sdir>/复盘.md（UTF-8）。**这一步必须做**，否则网站缺文字复盘。
 d. 用 mcp__qq-mail__SendMessage 发邮件，body_format=MARKDOWN，skip_confirmation=true。
    收件人严格用该 session 的 recipients 字段（[{"email":...}]），不要另读配置、不要增减：
      竞品号 → 3 个邮箱全填；自有号 → 只有 <自有号收件人>，绝不抄送同事。
    主题「[竞品复盘] <主播名> · <日期>」；is_self=true 时「[自有号复盘] …」。
    正文 = 步骤 b 正文 + 末尾追加：
      「---」+ 空行 +「🔗 在线查看完整报告（手机可点）」+ 该场 share_link.txt 的链接。
 e. **必须先用 list_messages 或等效方式确认邮件确实在「已发送」里，再写 email_sent.marker**
    （内容写发送时间 + 收件人数）。发送失败不写 marker，留给下一轮重试。

【步骤 4】本次至少发了 1 封才做：
 a. `python sync_all.py`（顺序敏感）
 b. workbuddy_sites_deploy：action=deploy，directory=<程序目录>\share\site，
    language=static，appName=竞品直播复盘报告中心，userAskedToPublish=true，domainPrefix 见下方注意
    每场在线地址 <根地址>/reports/<roomid>_<date>_<time>/index.html?sharecode=<分享码>
 c. `python build_index.py` 刷新本地看板

【注意】严格靠 email_sent.marker 去重；marker 存在即跳过；部署和刷看板只在有新发邮件时做；
        数据缺失一律「未获取」；复盘.md 与邮件正文保持一致。
```

> ⚠️ **易错点**：几个自动化任务的 `domainPrefix` 必须写成同一个 `<站点域名前缀>`，
> 否则报告会被部署到两个域名，旧链接直接失效。

## #2 漏发兜底（5/20/35/50 分）

```
竞品直播报告「漏发兜底」任务（幂等，靠 email_sent.marker 去重，绝不重复发信）。
工作目录：<程序目录>

【步骤 1】执行 `python watchdog.py --json`。
  扫描「有 ENDED + 有 报告.html + 无 email_sent.marker + 下播超过 15 分钟」的场次，输出：
  backlog_count / backlog[]，每项含 sdir、sdir_abs、room_id、name、title、date、time、
  ended_ago_min、is_self、recipients、share_link。

【步骤 2】backlog_count == 0 → 直接结束，不发邮件、不部署、不写任何文件。
          （正常情况绝大多数轮次都是空跑，这是设计如此）

【步骤 3】backlog_count > 0 → 逐场补发，标准与主任务完全一致：
 a. 读 sdir_abs 的 摘要.md + transcript.txt（大文件分段读完，不要只读开头）
 b. 写六节复盘正文（同主任务）
 c. 原样存 <sdir_abs>\复盘.md
 d. mcp__qq-mail__SendMessage，body_format=MARKDOWN，skip_confirmation=true；
    收件人严格用 recipients 字段；主题同主任务；正文末尾追加「---」+「🔗 在线查看完整报告」+ share_link；
    share_link 为空时改用 <share/base_url.txt>/reports/<room_id>_<date>_<time>/index.html?sharecode=<分享码>
 e. 先用 list_messages(dir=sent) 确认已在「已发送」，再写 email_sent.marker
    （写发送时间 + 收件人数 +「watchdog 补发」）。失败不写 marker。

【步骤 4】只要补发了至少 1 封：`python sync_all.py` → workbuddy_sites_deploy（domainPrefix=<站点域名前缀>）
          → `python build_index.py`。没有补发就都不做。

【注意】marker 存在即视为已发，跳过；不要因为「想确认一下」重发；数据缺失写「未获取」。
```

## #3 每日情报（每天 08:50）

```
竞品直播「每日情报」生成任务（幂等）。工作目录：<程序目录>

【步骤 1】目标日期 = 昨天（Asia/Shanghai）。
  执行 `python watchdog.py --json`，backlog_count > 0 先按兜底标准补发，补完再继续。

【步骤 2】扫描 recordings/*/<目标日期>/*/，有 transcript.txt 的算一场。
  一场都没有 → 直接结束，不做任何其他操作。

【步骤 3】完整读昨天逐字稿（核心工作，不能只看开头）：
  每场读 transcript.txt 全文 + meta.json + viewers.csv + 摘要.md。
  目的是抽情报，不是写逐场复盘。重点：
   ① 政策：新政策、考试安排、分数线、定向名额、招生方式、学校动向
   ② 对手动作：开群/内推/测评/签约班/探校、报价与承诺条款
   ③ 打法：钩子物料、口令、留资方式、转化链路、起量手法
   ④ 数据：能互相印证或互相矛盾的硬数据（多号口径不一致的特别有价值）
   ⑤ 风险：绝对化承诺、特殊渠道、组织举报、涉未成年人隐私
  同一事件多号都在讲时，横向对比口径差异，这往往最值钱。
  执行方法见 analysis-playbook.md（切分 → 主代理亲读关键场 + 子代理分组 → grep 抽检）。

【步骤 4】写 每日汇总/<目标日期>.intel.json（UTF-8 严格 JSON）：
  { date, headline, summary, kpis[[值,标签]...], intel[{cat,hot,title,body,accounts}], chances[[标题,说明]...] }
  cat 只能取 政策|对手动作|打法|数据|风险|自有号；hot 只给 4-6 条；
  intel 12-18 条按重要性排序，提炼成跨场主题，不要逐场罗列；chances 4-5 条要能落地。
  全部中文；所有数字来自逐字稿或 viewers.csv，不许估算编造。

【步骤 5】`python daily_intel.py <目标日期>` → `python sync_all.py`

【步骤 6】workbuddy_sites_deploy：directory=<程序目录>\share\site，language=static，
  appName=竞品直播复盘报告中心，domainPrefix=<站点域名前缀>，userAskedToPublish=true。
  部署后 WebFetch 核对 <报告站根地址>/daily/<日期>.html?sharecode=<分享码>
  可访问、情报条数与 json 一致。

【注意】情报质量比数量重要，宁可 12 条全硬不要 18 条注水；这是离线整理，不需要发邮件。
```

## #4 心跳保活（每小时）

```
每小时检查「竞品直播间监控」是否在运行，停止则重新后台拉起。
这是 WorkBuddy 会话期间的兜底；真正 24h 无人值守仍需 Windows 计划任务。

1. Bash 执行：
   python -c "import os,time; p=r'<程序目录>\state.json'; print('DEAD' if not os.path.exists(p) else ('DEAD' if time.time()-os.path.getmtime(p)>900 else 'ALIVE'))"
2. 输出 ALIVE → 什么都不做，结束。
3. 输出 DEAD → Bash（run_in_background=true，cwd=<程序目录>/dlm）执行：
   cd <程序目录>/dlm && python monitor.py
注意：不写任何数据、不向外发任何消息，不做与保活无关的操作。
```

## #5 每日汇总推送 — PAUSED，保持关闭

原设计 09:05 把 `每日汇总/<date>.md` 邮件发给 <自有号收件人>。已被 #3 的在线情报页取代，
启用会造成重复打扰。**保持 PAUSED，不要改成 ACTIVE。**

---

## 重建顺序

1. 先确认本地采集层在跑（`healthcheck.py` → `verdict: OK`）
2. 建 #4 心跳（保证会话期不断）
3. 建 #1 主推送、#2 兜底（先跑 `python watchdog.py --json` 确认无积压再启用，避免一上来补发一堆旧场次）
4. 建 #3 每日情报
5. 注册两个 Windows 计划任务并重启一次电脑
6. 第二天核对：邮件数 = 场次 marker 数 = 站点报告数
