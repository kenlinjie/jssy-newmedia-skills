# 逐字稿 → 每日情报：提炼流水线

一天 10-20 场、十几万到上百万字符的纯口语逐字稿，硬读会崩。这套流水线已连续验证两周，照做。

## 核心原则

情报的价值不在"某账号直播了"，而在**跨场次的主题 + 各号口径冲突**。
20 场逐场罗列 = 废稿；同一件事三个号三种说法 = 金矿。

---

## Step 0 先清积压

```bash
python watchdog.py --json
```

`backlog_count > 0` 先按兜底标准补发，再开始读稿。否则当天情报会缺场次。

## Step 1 盘点当天素材

```bash
curl -s ... # 不用
# 直接列目录
ls recordings/*/2026-11-06/*/transcript.txt
```

凡是当天目录下有 `transcript.txt` 的算一场。同时确认每场的 `viewers.csv` 和 `meta.json`。

先算规模，决定分组：

```
场次数 / 账号数 / 总时长 / 单场峰值 / 累计观看 / 已发封数
```

这六个数直接就是 `intel.json` 的 `kpis`。

## Step 2 切分逐字稿（必做）

逐字稿是纯口语、**整段没有换行**，一行几万字。先按标点切成 240-260 字/行，写临时文件：

```python
# 写成 _tmp/split.py 再执行，不要用 python -c（反斜杠路径会 SyntaxError）
import os, re, glob
BASE = r"<程序目录>"
day = "2026-11-06"
out_dir = os.path.join(BASE, "_tmp", day)
os.makedirs(out_dir, exist_ok=True)

for p in glob.glob(os.path.join(BASE, "recordings", "*", day, "*", "transcript.txt")):
    sdir = os.path.dirname(p)
    key = os.path.basename(os.path.dirname(os.path.dirname(sdir))) + "_" + os.path.basename(sdir)
    text = open(p, encoding="utf-8", errors="replace").read()
    parts = re.split(r"(?<=[。！？；])", text)
    lines, buf = [], ""
    for seg in parts:
        buf += seg
        if len(buf) >= 240:
            lines.append(buf.strip()); buf = ""
    if buf.strip():
        lines.append(buf.strip())
    with open(os.path.join(out_dir, key + ".txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(l for l in lines if l))
    print(key, len(lines), "行")
```

这样每行有语义、带行号好引用。

## Step 3 分层读（关键）

**不要平均用力。** 按信息密度分配：

1. **主代理亲读 2-4 场**——挑当天信息密度最高的。经验排序：
   - 数据型头部号（逐区扒名额分布，信息密度最高）
   - `老周讲升学`、`新蓝升学（新龙文）`（长场次、大量硬数字）
   - 政策解读型账号（口径争议的源头）
2. **其余场次分 2-5 组，交子代理并行**，每组的指令必须包含这几项（缺一项质量就掉）：

   > 从这份逐字稿里逐条摘录，每条给：①原话（不要转述）②时间点或行号 ③涉及的数字/名额/分数线/费用
   > 另单独给出两节：
   > **A. 口径疑点**：讲得前后矛盾、或与其他号说法对不上的地方
   > **B. 同一账号上下半场冲突**：同一个主播在上半场和下半场对同一件事给了不同数字/说法的，全部列出来
   > 不要写总结，只做摘录。

   子代理产出的「口径疑点」和「上下半场冲突」两节，往往直接变成情报里的 hot 条目。

## Step 4 grep 回原文抽检（必做）

ASR 会把数字读错（616 读成 718、57 读成 51）。**所有关键数字写进情报前，必须 grep 回原文确认**：

```bash
grep -o -E ".{40}616.{40}" _tmp/2026-11-06/*.txt
grep -n "定向" _tmp/2026-11-06/*.txt | head
```

抽检对象：分数、人数、名额、金额、日期、学校名。抽检不通过的，宁可写"口径存疑"也不要照抄。

## Step 5 归并成主题

把摘录按六类归档，跨场次合并同一事件：

| cat | 抓什么 | 判定 |
|---|---|---|
| 政策 | 新政策、考试安排、分数线、定向名额、招生方式变化 | 官方口径 or 多号一致 |
| 对手动作 | 开群、内推、测评、签约班、探校、报价与承诺条款 | 谁在做什么新动作 |
| 打法 | 钩子物料、口令、留资方式、转化链路、起量手法 | 可被我们抄的 |
| 数据 | 能互相印证或互相矛盾的硬数据 | **多号不一致的优先** |
| 风险 | 绝对化承诺、特殊渠道、组织举报、涉未成年人隐私 | 合规相关 |
| 自有号 | 我们自己两个号的表现 | 对照用 |

排序：hot（4-6 条，当天最重磅）→ 口径冲突 → 政策 → 对手动作 → 打法 → 风险 → 数据 → 自有号。

## Step 6 写 `intel.json`

结构见 `architecture.md`。几条硬要求：

- `title` 要有信息量。「新淮贯通班降 60 分引争议」可以，「夏老师直播讲贯通班」不行。
- `body` 必须写清**谁、什么时间、说了什么原话、什么数字**。多号冲突就把各家说法并列。
- 数字全部可回溯到逐字稿或 `viewers.csv`，写不出出处的判断直接删。
- `chances` 站在「本机构小升初新媒体运营」立场，要能当天落地
  （例："做一张《定向降分自查表》，按校列名额/去年用掉/实际降几分"）。
- 宁可 12 条全硬，不要 18 条注水。

## Step 7 渲染 + 上线

```bash
python daily_intel.py 2026-11-06
python sync_all.py
```

然后部署 `share\site`（`domainPrefix=<站点域名前缀>`），再用 WebFetch 核对页面：
情报条数、KPI 六项、场次链接数是否与 json 一致。**不核对就等于没交付。**

---

## 常见返工原因

| 症状 | 原因 | 修法 |
|---|---|---|
| 页面空白/情报不显示 | `.intel.json` 结构写错（把 kpis 写成对象） | `kpis` / `chances` 是二元组数组 |
| 站点看不到当天情报 | 只生成了 `.md` 没 `.html` | `scan_daily()` 只认 html，重跑 `daily_intel.py` |
| 情报数字和原文对不上 | ASR 误读，没回原文抽检 | Step 4 |
| 条目像流水账 | 逐场罗列，没做跨场归并 | 按事件合并，多号并列口径 |
| 漏了最值钱的那条 | 只读了前 300 行 | 亲读关键场次整场，别抽样开头 |
