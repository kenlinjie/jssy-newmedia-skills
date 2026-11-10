# 迁移到新机器 / 从零部署

适用：一台国内网络、不翻墙、24 小时开机的 Windows 工作机。程序目录默认 `<程序目录>`。
完整原始清单在 `dlm\部署清单.md`，本文是可执行精简版。

## 前提

- Windows 10/11，**关闭睡眠/休眠**（电源设置 → 永不睡眠），插电。
- 目标机与 WorkBuddy 在**同一台机器**、D 盘路径一致（自动化提示词里路径写死，换路径要全局替换）。
- 合规：不开浏览器、不登录、代码不写 Cookie；只录音频、不录视频、不抓弹幕。

## 1. 环境

```bat
:: Python 3.13 x64，安装时勾选 Add python.exe to PATH
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ^
    streamget==4.0.10 imageio-ffmpeg numpy sherpa-onnx==2.0.1
```

模型放到 `dlm\models\`，**三个缺一不可**：

| 文件 | 大小 | 来源 |
|---|---|---|
| `model.int8.onnx` | ~228MB | hf-mirror.com（已验证可达），或随目录一起拷过去 |
| `tokens.txt` | 小 | 同上 |
| `silero_vad.onnx` | ~1.7MB | 同上 |

自检：`python -c "import monitor,asr,report,cli,daemon; print('模块导入 OK')"`

## 2. 拷贝程序

把整个 `dlm` 目录复制到目标机 `<程序目录>\`（含 `models/`、`share/`，不含 `recordings/` 亦可，历史数据另算）。

核对 `watchlist.txt`：每行 `抖音号  # 账号名`，`#` 开头是注释。

## 3. 唯一必改项：`launch.bat`

```bat
set "PY=<Python路径>"
set "BASE=<程序目录>"
```

- 换成目标机真实 Python 路径；找不到时 `launch.bat` 会自动回退到 PATH 里的 `python` / `py`。
- 目录若不同，`install_task.xml` 与 `digest_task.xml` 里指向 `launch.bat` / `WorkingDirectory` 的两条路径也要同步改。

## 4. 注册计划任务（开机/登录自启）

**右键 `install_tasks.bat` → 「以管理员身份运行」**。
⚠️ 不是双击：bat 不会弹 UAC，普通权限注册 SYSTEM 任务会失败。

黑窗口应显示两行 `[OK]`：监控守护已注册 / 每日汇总已注册。
若乱码或没有 OK，用管理员 CMD 手动执行（能看到真实英文报错）：

```bat
schtasks /Create /TN "竞品直播间监控" /XML "<程序目录>\install_task.xml"
schtasks /Create /TN "竞品直播间每日汇总" /XML "<程序目录>\digest_task.xml"
schtasks /Query /TN "竞品直播间监控"
```

状态应为 `Ready`。**注册成功后重启一次电脑**，监控改由 SYSTEM 账户 24h 常驻（不登录、睡眠也照跑）。

## 5. 配自动化

按 `automations.md` 建 4 个 ACTIVE 任务（心跳 → 主推送 → 兜底 → 每日情报）。
**先用 `healthcheck.py` 确认采集层 OK、`watchdog.py --json` 确认积压为 0 再启用**，否则新任务会把历史场次一次性补发成堆邮件。

## 6. 配站点与收件人

| 文件 | 内容 |
|---|---|
| `share/base_url.txt` | `<报告站根地址>` |
| `share/sharecode.txt` | 分享码，如 `<分享码>` |
| `share/recipients.txt` | 竞品场次收件人，每行一个邮箱 |
| `share/recipients_self.txt` | 自有号场次收件人（通常只自己） |
| `share/self_rooms.txt` | 自有抖音号白名单 |

部署目录 `share\site`，`appName=竞品直播复盘报告中心`，`domainPrefix=<站点域名前缀>`。
部署幂等，重复部署只更新内容、根地址不变。

## 7. 验收

| 验收项 | 怎么测 | 期望 |
|---|---|---|
| 模块导入 | `python -c "import monitor,asr,report,cli,daemon"` | OK |
| 状态 | `python cli.py status` | 守护运行中，各号 polling |
| 体检 | `python <skill>/scripts/healthcheck.py` | `verdict: OK` |
| 单号检测 | `python cli.py check <抖音号>` | 返回状态/人数/拉流地址 |
| 开播自动录 | 等某个竞品真实开播 | `recordings/<号>_<名>/<日期>/<时间>/` 下出现 viewers.csv、flac、transcript.txt、报告.html、摘要.md；下播写 `ENDED` |
| 移除即停 | `python cli.py remove <抖音号>` | 该号停止轮询；正直播则收尾出报告 |
| 无人值守 | 重启**不登录** | `cli.py status` 仍显示运行中 |
| 每日汇总 | `python digest.py 2026-11-06` | 生成 `每日汇总/<date>.md` + `.html` |
| 报告闭环 | 下一轮自动化 | 邮件已发送 + `复盘.md` + `email_sent.marker` + 站点报告数一致 |

## 8. 日常配置调节（`config.json`）

| 字段 | 默认 | 含义 |
|---|---|---|
| `poll_interval_sec` | 180 | 未开播轮询间隔 |
| `live_sample_sec` | 60 | 直播中在线人数采样间隔 |
| `per_request_gap_sec` | 2.0 | 单次请求间隔，别调太小 |
| `segment_sec` | 600 | 单段录音秒数 |
| `min_free_gb` | 10 | 剩余空间低于此值暂停录制 |
| `asr_threads` | 4 | 转写线程数 |
| `session_merge_gap_sec` | 600 | 短断流合并窗口 |
| `max_recordings` | 3 | **死配置，代码从不读取**，别当并发上限 |

改 `config.json` 后需重启监控生效；改收件人/白名单无需重启。

## 9. 换路径时的全局替换清单

`<程序目录>` 出现在这些地方，漏一处就会静默失效：

1. `launch.bat` 的 `BASE`
2. `install_task.xml` / `digest_task.xml` 的 `Command` 与 `WorkingDirectory`
3. 4 个自动化任务的 `prompt` 正文与 `cwds`（见 `automations.md`）
4. `healthcheck.py` 的 `DEFAULT_BASE`（或用环境变量 `DLM_BASE` 覆盖）
