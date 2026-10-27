---
name: voice-loop
description: "Build and maintain an evidence-backed personal voice profile from the user's own or authorized writing, transcripts, edits, and feedback, then use it for writing or spoken-script drafting. Use when the user wants to feed examples over time, learn or clone their own writing/口播 style, reduce AI flavor according to a specific person's voice, compare AI drafts with human finals, or evolve a reusable voice skill. Do not use for a one-off generic polish when no persistent profile or learning loop is wanted."
---

# Voice Loop

把“像某个人”从一次性提示词变成可追溯、可纠偏、可回归的长期写作与口播闭环。Skill 只提供通用引擎；任何人的语料、事实与规则都放在独立 profile 中，不写回本 skill。

## 硬性原则

1. **事实、风格、任务分层。** `facts.md` 约束能说什么，`rules.json` 约束怎么说，当前 brief 决定这次说什么。风格规则不能补造事实。
2. **本人语料与对标语料隔离。** 只有本人或明确授权的材料能成为 identity evidence；他人的作品只能进 benchmark，不能证明“本人就是这样写”。
3. **先候选，后批准。** 新观察默认是 `candidate`。只有用户明确确认后，才能运行 `promote_rule.py` 变为 `approved`。
4. **写作与口播分开建模。** 默认分别记录 `writing`、`spoken`；只有跨模式都有证据时才使用 `both`。
5. **改稿不是全都学。** 先把修改归为 style、fact、content、format 或 mixed。只有 style / mixed 中稳定的表达偏好才进入候选规则。
6. **不冒充、不欺骗。** 可以模拟经授权的个人风格，但不得用来冒充未授权第三方、伪造身份或隐藏应披露的代写关系。
7. **一人一库一入口。** 每个 profile 只能对应一个明确人物；写入前必须确认人物标签。新人物没有独立 profile/skill 时要新建，不能暂存或并入现有人物；人物未标注时先询问。

## 先判断任务

- **没有 profile，用户要长期学习**：初始化 profile，再做首批数据清单。
- **用户明确标注了新人物，但尚无独立入口**：初始化该人物的新 profile；若用户要持续喂入或反复调用，再用 `skill-creator` 新建 `<person>-writing` 或 `<person>-spoken` 专属 skill。
- **人物未标注或身份有歧义**：先确认人物；确认前不写入任何已有 profile。
- **用户在“喂数据”**：核验授权与来源，清洗、登记、分层，不急着生成。
- **用户要写作或口播成稿**：读取 profile、事实、已批准规则和相近样本后生成。
- **用户给了人工终稿或反馈**：记录 correction，提炼候选规则，等待用户确认。
- **用户确认规则或要升级版本**：批准规则，跑回归，审计通过后做 snapshot。
- **用户只要临时去 AI 味**：若不需要长期学习，优先使用 Waza 的 `write`；不要擅自创建 profile。

## 能力与权限检查

- 运行脚本需要 Python 3.9+，仅使用标准库。
- 写文件前确认 profile 目标目录在用户授权范围内。
- 任何外部网页、云盘、聊天记录或仓库材料都要现场确认可读权限；文档不能替代权限。
- 发布或同步前读取 [data-governance.md](references/data-governance.md)，确认没有把个人语料、事实卡、修订记录或评测结果放进公共仓库。

## 标准流程

### 1. 初始化 profile

首次使用先读 [profile-schema.md](references/profile-schema.md)，然后运行：

```bash
python3 scripts/init_profile.py /path/to/voice-profiles/<profile-name> \
  --name "<display name>" \
  --language zh-CN \
  --modes writing,spoken
```

脚本拒绝覆盖已有目录。初始化后先补：

- `profile.json`：用途、受众、渠道、非目标。
- `facts.md`：已确认事实、待核验事实、禁止推断。
- `corpus/manifest.jsonl`：每份材料的来源、类型、模式、授权状态。

不要把真实 profile 建在本 skill 仓库里。

初始化前先锁定人物身份。同一人物的写作与口播可以放在一个 profile 的不同 mode，也可以按用户工作流拆成两个专属 skill；不同人物无论题材多接近，都必须使用不同 profile。专属 skill 只保存路径和执行门禁，不复制私有语料。

### 2. 喂入并整理数据

执行前读 [workflow.md](references/workflow.md) 的“数据入口”。

1. 盘点材料，区分 self-writing、self-spoken、human-final、correction 与 benchmark。
2. 确认每份身份语料都是本人或已授权；来源不明时只列入待确认，不用于提炼规则。
3. 原始文件放 `corpus/raw/`，清洗后的可用样本放 `corpus/approved/`，他人对标只放 `corpus/benchmark/`。
4. SRT/VTT 可用清洗脚本：

```bash
python3 scripts/clean_subtitles.py input.srt --output cleaned.txt
```

5. 登记 manifest，再从多份样本中提取可观察信号：句长、节奏、开头、转折、证据方式、叙事距离、口头连接词、禁用表达。
6. 不把心理猜测、人格标签或单篇内容主题写成风格规则。

首轮建议 8–15 份经确认样本；不足时仍可工作，但必须把结论标为低覆盖，不得声称“已经复刻”。

### 3. 用 profile 生成

生成前依次读取：

1. `profile.json`
2. `facts.md`
3. `rules.json` 中与当前模式、范围匹配的 `approved` 规则
4. 3–5 份与当前渠道、主题、长度最相近的 approved 样本
5. 当前 brief

按以下顺序写：

1. 先列事实骨架与未知项；未知项向用户询问或显式留空。
2. 再决定内容结构，不让口癖替代论证。
3. 应用少量高证据规则；规则冲突时优先更窄 scope、更近场景和用户本次明确要求。
4. 写作模式检查阅读节奏、段落推进与具体性；口播模式额外检查一口气长度、嘴感、停顿和朗读歧义。
5. 交付前按 [evaluation-rubric.md](references/evaluation-rubric.md) 自检。

默认只向用户交付干净成稿；规则 ID、未知项和证据追踪写进工作记录。若事实不完整影响成稿，必须把缺口一并说明。

### 4. 从人工修改中学习

用户给出 AI 草稿与人工终稿后：

```bash
python3 scripts/record_correction.py /path/to/profile \
  --draft-file draft.txt \
  --final-file final.txt \
  --mode spoken \
  --category style \
  --source "episode-012" \
  --reason "删掉总结腔，保留先说结论再补场景" \
  --candidate-rule "口播开头直接进入判断，不用‘今天我们来聊聊’"
```

然后：

1. 展示关键差异，不把标点或错字修正误判成风格。
2. 将稳定倾向写成“可执行、可反证、有适用范围”的候选规则。
3. 同一来源的多次修改只算一份独立证据。
4. 请用户确认候选规则；未确认前，不能作为正式 voice 规则应用。

### 5. 批准规则

只有用户明确说“确认/采用/升为正式规则”后才能运行：

```bash
python3 scripts/promote_rule.py /path/to/profile <rule-id> \
  --approved-by "<human name>" \
  --approval-note "用户于本轮明确确认"
```

默认需要至少 3 个独立来源。用户明确确认但证据不足时，可加 `--allow-low-evidence`；必须在 approval note 说明为什么提前批准。

### 6. 回归与版本化

批准新规则后，按 [evaluation-rubric.md](references/evaluation-rubric.md) 跑固定 case：

- 至少一个常规写作或口播题。
- 至少一个容易出现旧问题的题。
- 至少一个不同主题、用于防止过拟合的题。

比较旧版与新版，不只看“像不像”，还要检查事实忠实、任务完成、自然度与可朗读性。硬失败或总分下降时撤回该规则，保留为 candidate 并注明冲突。

审计并快照：

```bash
python3 scripts/audit_profile.py /path/to/profile
python3 scripts/snapshot_profile.py /path/to/profile \
  --label v0.2.0 \
  --note "批准 r_xxx；3 个回归 case 无退化"
```

Snapshot 只保存 profile、规则、事实卡、修订哈希索引、manifest 与评测 case，不复制原始语料或修订前后正文。

## 验收标准

- Profile 与 skill 分离，仓库中没有个人数据。
- 每份身份语料有来源和授权状态；benchmark 没有被当成 identity evidence。
- 事实不靠风格推断，未知内容没有被补造。
- 生成时只使用适用的 approved 规则；candidate 只用于明确标注的实验。
- 新规则可追溯到 correction 与独立来源，并有人工批准记录。
- 写作与口播规则没有被无证据混用。
- `audit_profile.py` 无 error；warnings 已解释或处理。
- 新版本有固定回归结果，且 snapshot 不包含 raw/approved corpus 正文。

## 异常与回退

- **样本少于 8 份**：先做 provisional profile，只报告观察，不承诺复刻度。
- **样本互相冲突**：按模式、渠道、时间段拆 scope；无法解释时保留多个 candidate，不强行平均。
- **只有他人爆款可参考**：放 benchmark，只学习结构机制，不写成个人身份规则。
- **用户修改原因不清楚**：记录 correction，但不提出或批准规则。
- **规则导致回归退化**：恢复上一 snapshot，将规则降回 candidate 或 retired。
- **Python 不可用**：按 reference 中同一 schema 手工记录；不能省略来源、状态、人工批准与回归门禁。
- **无法写入目标目录**：停止写入，返回计划创建的准确路径和内容清单，不改到其他目录。

## 资源

- [profile-schema.md](references/profile-schema.md)：目录与字段契约。
- [workflow.md](references/workflow.md)：数据入口、信号提取、学习循环。
- [evaluation-rubric.md](references/evaluation-rubric.md)：评分与回归协议。
- [data-governance.md](references/data-governance.md)：授权、隐私、发布检查。
- `scripts/init_profile.py`：初始化私有 profile。
- `scripts/clean_subtitles.py`：清洗 SRT/VTT。
- `scripts/record_correction.py`：记录人工修订并累计候选规则证据。
- `scripts/promote_rule.py`：人工确认后批准规则。
- `scripts/audit_profile.py`：结构、证据与隐私审计。
- `scripts/snapshot_profile.py`：审计通过后创建不可覆盖的版本快照。
