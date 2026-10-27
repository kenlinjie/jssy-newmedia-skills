---
name: local-sota-transcription
description: 在 Apple Silicon Mac 上分级完成本地离线音视频转写：普通内容优先使用 macOS SpeechAnalyzer，正式中文长音频默认使用轻量 Qwen3-ASR-0.6B-8bit，按需二阶段加载 ForcedAligner，困难片段再回退 1.7B 或用 Whisper 独立复核；生成可恢复检查点、时间戳、JSON/SRT/Markdown/TXT 和完整性验收。用于会议、访谈、口播、内部或敏感录音、数小时媒体、云端 ASR 超时/丢任务，以及用户要求不上传第三方时。
---

# 本地轻量分级转写

> 省域包适配（2026-10-27）：执行命令前，把 `SKILL_DIR` 设为当前 `SKILL.md` 所在目录的绝对路径。随包只含技能源码、模板与静态资产；运行时和账号按实际环境配置。


优先满足准确度要求，再选择负担最低的本地路径。不要同时加载多个 ASR，
也不要为了普通转写默认启用逐词对齐。

## 路由

1. **普通录音、草稿、快速浏览**：先用 Apple `SpeechAnalyzer`。它复用系统
   语言资源，当前机器必须已经安装目标语言；Skill 不自动下载系统资源。
2. **正式中文、长音频、术语较多或需要中断恢复**：默认用
   `Qwen3-ASR-0.6B-8bit`，先生成粗粒度分块时间戳。
3. **明确需要逐词时间戳或最终字幕**：在同一 Qwen 输出目录补跑
   `--align`。脚本复用 ASR 检查点，卸载 ASR 后才加载 ForcedAligner。
4. **噪声、方言、复杂专名或 0.6B 抽检失败**：只对必要片段或任务显式
   指定保留的 `Qwen3-ASR-1.7B-8bit`，不要把它恢复成默认。
5. **关键人名、数字、日期、否定词和决策**：用已有 Whisper CPU 链做
   短片段独立复核，不把 Whisper 当数小时主转写。

Apple 路线适合正常对话和一般用途，但没有本任务标注集上的中文准确率保证，
也不提供说话人身份。正式稿仍应使用 Qwen 并抽听关键片段。

## 边界

- 默认全程本地处理，不上传录音、逐字稿或会议术语。
- 只有用户明确授权外部服务后，才可把云端 ASR 当作额外路径。
- Apple 与 Qwen 均不输出可靠说话人身份。不得把分段编号猜成人名；结合
  报幕、称呼和上下文仍不确定时，保留时间点并标注待确认。
- `complete` 只表示源哈希读回、计划范围和输出文件通过程序校验，不表示
  专有名词、数字和发言归属已经人工听辨。

## 首次安装与预检

固定运行时缺失时，在获准联网和写入本地运行目录后执行：

```bash
"$SKILL_DIR"/scripts/bootstrap_runtime.sh
"$HOME/.local/share/codex-local-asr/venv/bin/python" \
  "$SKILL_DIR"/scripts/install_lightweight_model.py
```

安装脚本固定仓库 revision、权重字节数和 SHA-256，不删除已有 1.7B 或
ForcedAligner。仅验签已有安装：

```bash
"$HOME/.local/share/codex-local-asr/venv/bin/python" \
  "$SKILL_DIR"/scripts/install_lightweight_model.py \
  --verify-only
```

任何正式转写前先运行对应命令的 `--preflight`，确认源文件、目标目录、
语言资源、运行时和模型边界。

## 路线 A：Apple 极轻量转写

```bash
/usr/bin/python3 \
  "$SKILL_DIR"/scripts/transcribe_with_apple.py \
  "/absolute/path/to/audio.mp3" \
  --output-dir "/absolute/path/to/apple-transcript" \
  --locale zh_CN \
  --preflight
```

预检通过后去掉 `--preflight`。Apple 输出的
`timing_mode=apple-audio-time-range` 是语句/片段对应音频范围，不得表述成
Qwen ForcedAligner 的逐词时间戳。该路线不做 Qwen 式分块恢复；超长正式录音
直接走路线 B。

## 路线 B：Qwen 可恢复长音频

先把术语、参会人、车型或部门名写入 UTF-8 上下文文件。上下文必须是
候选词或背景，不得写成要求模型补全的结论。

```bash
"$HOME/.local/share/codex-local-asr/venv/bin/python" \
  "$SKILL_DIR"/scripts/transcribe_long_audio.py \
  "/absolute/path/to/audio.mp3" \
  --output-dir "/absolute/path/to/qwen-transcript" \
  --language Chinese \
  --context-file "/absolute/path/to/context.txt"
```

默认以 240 秒分块、4 秒重叠串行处理，使用 0.6B 模型并生成粗粒度时间戳。
每个成功分块立即写入原子检查点；中断后用完全相同的命令和输出目录重跑。
若源文件、模型、参数或上下文指纹不同，脚本拒绝复用旧目录。

需要逐词时间戳时，在原命令末尾加 `--align` 并复用原输出目录。脚本先完成
或复用全部 ASR 检查点，释放 ASR 与 MLX 缓存，再串行加载对齐器；对齐阶段
也逐块保存，可再次恢复。

仅测试小片段时使用 `--start-seconds` 与 `--duration-seconds`。0.6B 抽检不合格
时才显式回退：

```bash
--asr-model "$HOME/Library/Caches/codex-local-asr/models/Qwen3-ASR-1.7B-8bit"
```

## 输出与验收

两条路线都读取：

- `manifest.json`：运行指纹、完成范围、失败点和最终状态；
- `verification.json`：源文件 SHA-256 读回、输出哈希和时间戳模式；
- `transcript.json`：结构化片段；Qwen 对齐模式另含逐词时间戳；
- `transcript.srt`、`transcript.md`、`transcript.txt`：后续整理版本。

只有 `manifest.status=complete` 且 `verification.status=passed` 时，才称这次
本地转写完成。还必须按需求核对 `timing_mode`：

- `coarse`：Qwen 分块级时间戳；
- `word`：Qwen 逐词对齐完整；
- `mixed`：请求的对齐不完整，必须按原命令恢复，不能交付为逐词稿；
- `apple-audio-time-range`：Apple 语句/片段范围。

Whisper 短片段复核：

```bash
"$SKILL_DIR"/scripts/verify_clip_with_whisper.sh \
  "/absolute/path/to/audio.mp3" START_SECONDS DURATION_SECONDS \
  "/absolute/path/to/review-output"
```

ASR 冲突时以清晰音频为准；仍无法确认时保留源文件名与时间点，不补猜。

## 故障处理

- `No Metal device available`：当前进程无法访问 Metal；改到可访问本机 GPU
  的执行边界，不切到 CPU 冒充同等性能。
- Apple 报语言资源未安装：停止并说明；Skill 不自动修改系统语言资源。
- 模型目录缺文件、字节数或 SHA 不符：停止，重新下载并验签；不得跳门禁。
- Qwen 分块或对齐中断：保留 `chunk-results/`，用原命令恢复。
- 16 GB 内存压力：保持 `batch_size=1`，先关闭 `--align`；仍紧张时把
  `--chunk-seconds` 降到 180。不要并行运行 Apple、Qwen、对齐器或 Whisper。
- 需要选型依据、固定版本与能力边界时，读取
  [references/model-selection.md](references/model-selection.md)。
