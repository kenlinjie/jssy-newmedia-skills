---
name: watch
description: 本地优先观看和分析 URL 或本地视频：优先取原生中英文字幕，用 ffmpeg 提取去重关键画面，无字幕时调用本机 Qwen3-ASR 并验证完整性，再基于画面与时间戳逐字稿回答。用于用户要求看视频、概括视频、分析口播/画面/钩子/结构、定位某个时间点、诊断录屏，或输入 /watch、视频链接、mp4/mov/mkv/webm 路径时。
---

# Watch：本地优先视频理解

把视频拆成两条可核对证据：画面帧与带时间戳逐字稿。默认不把音频上传第三方。

## 预检

把 `SKILL_DIR` 设为当前 `SKILL.md` 所在目录的绝对路径，并确认入口存在：

```bash
SKILL_DIR="<当前 watch Skill 的绝对目录>"
test -f "$SKILL_DIR/scripts/watch.py"
python3 "$SKILL_DIR/scripts/setup.py" --json
```

- `can_proceed=true`：直接执行。
- `first_run=true`：运行一次 `python3 "$SKILL_DIR/scripts/setup.py"` 写入本地优先默认值。
- `can_proceed=false`：按 JSON 中的 `missing_binaries` 或 `local_asr.checks` 修复后再执行。
- 不主动索要 Groq/OpenAI 密钥。只有用户明确授权云端转写并选择 `--asr api` 时才配置密钥。

## 执行

先分离视频来源与用户问题，再选择最小充分的画面预算：

- 只问讲话内容：`--detail transcript`。
- 需要同时理解讲话与画面：默认 `--detail balanced`。
- 先快速扫视：`--detail efficient`。
- 用户明确要求不漏场景且接受高消耗：`--detail token-burner`。
- 点名某个时间或区间：一定传 `--start` / `--end`，不要稀疏扫描整段长视频。

基本命令：

```bash
python3 "$SKILL_DIR/scripts/watch.py" "<URL 或绝对路径>" \
  --detail balanced \
  --out-dir "<任务目录下的 watch-work>"
```

常用参数：

- `--start T --end T`：`SS`、`MM:SS` 或 `HH:MM:SS`。
- `--timestamps T1,T2`：强制抓取逐字稿中“看这里”等指示语对应画面。
- `--max-frames N`：收紧画面预算。
- `--resolution 1024`：只有需要读小字、代码或表格时使用；其他情况保持 512。
- `--language Chinese|English|...`：指定本地 Qwen3-ASR 语言，默认 `Chinese`。
- `--context-file FILE`、`--term 术语`：给中文专名、车型、公司或人名提供候选上下文；不得写成要求模型补全的结论。
- `--asr off`：没有字幕时只看画面。
- `--asr api --whisper groq|openai`：仅在用户明确授权音频外发时使用。
- 默认先通过 `yt-dlp --cookies-from-browser chrome` 使用本机登录态；读取失败或没有产物时自动降级为公开无 cookie 访问。
- `--cookies-from-browser BROWSER`：改用其他浏览器或指定 profile（也可设置 `WATCH_COOKIES_FROM_BROWSER`）。
- `--cookies-file FILE`：改用用户提供的 Netscape 格式 cookie 文件。
- `--no-cookies`：本次完全禁用 cookie 访问。

默认顺序固定为：原生中文字幕 → 原生英文字幕 → 本地 Qwen3-ASR。原生字幕存在时不重复跑 ASR。

## 读取与判断

1. 读取脚本输出的每个 frame 路径；在 Codex 中用本地图片查看工具批量查看，保持时间顺序。
2. 对照逐字稿时间戳定位画面。指示语对应画面可能没有场景切换，必要时用 `--timestamps` 二次抓取。
3. 回答中区分“画面可见”“口播明确说出”“综合推断”，关键结论附时间点。
4. 用户只问一个具体问题时直接回答，不强行生成全片报告。
5. `transcript` 模式也要总结，不要把整份逐字稿倾倒进聊天；用户明确索要原文时再交付。

## 本地 ASR 门禁

本地链调用现有 `local-sota-transcription`：默认先用
`Qwen3-ASR-0.6B-8bit` 完成可恢复转写，释放 ASR 后再显式运行 `--align`。
`watch` 依赖精确时间点定位画面，因此这里必须完成串行逐词对齐；只有 0.6B
对关键内容抽检失败时，才通过 `WATCH_LOCAL_ASR_MODEL` 显式回退保留的 1.7B。

只有下列条件同时满足，才把逐字稿用于语义结论：

- `local-asr/manifest.json` 的 `status=complete`；
- `local-asr/verification.json` 的 `status=passed`；
- `local-asr/transcript.json` 的 `status=complete`。
- `verification.json` 与 `transcript.json` 的 `timing_mode=word`，且
  `chunks_aligned=chunks_expected`、逐词数组非空。

失败或中断时保留 `local-asr/`，以同一命令和输出目录恢复；不得把
`partial`、`coarse` 或 `mixed` 当作可定位画面的完整逐词稿。人名、品牌、
数字、日期、否定词与关键决策仍有疑点时，加载 `local-sota-transcription`，
截取短片段用本地 whisper.cpp 独立复核。

## 能力路由

需要处理平台受限下载、进入剪辑、生成 MG、制作字幕或封面时，读取 [references/capability-routing.md](references/capability-routing.md)，只加载与当前请求有关的本机 Skill。`watch` 本身只负责取得和解释视频证据，不擅自扩成剪辑或发布任务。

## 安全与收尾

- URL 由本机 `yt-dlp` 访问；默认只让 `yt-dlp` 读取浏览器 cookie 并直接用于目标站点请求。脚本不打印 cookie 值、不复制 cookie 数据库，也不读取 localStorage 或密码；cookie 不可用时自动降级为公开访问。
- 默认本地 ASR，不上传视频或音频。云端 API 路径必须有本次明确授权。
- 只写 `--out-dir` 或自动生成的精确工作目录，不修改源视频。
- 为后续追问保留工作目录。仅在用户确认不再使用时清理精确生成目录；不要广泛删除或触碰源素材。
- 下载失败时报告平台、登录或地区限制，不做无界重试。

上游帧抽取核心来自 `bradautomates/claude-video`（MIT），本安装已按本机能力改为 Codex、本地中文 ASR 与可验证证据工作流。
