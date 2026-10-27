# 本机能力路由

只在用户请求超出“看懂视频”时加载对应 Skill，避免一次任务启动整条制作链。

## 获取视频

- 公开且 `yt-dlp` 支持：继续使用 `watch` 自带下载器。
- 平台限制公开下载：`watch` 默认先通过 `yt-dlp` 使用浏览器 cookie，读取失败或没有产物时自动重试公开访问。仍失败再加载 `agent-reach`，按该 Skill 的平台边界获取规范化 URL 或媒体。
- 已知抖音直播间是否真的在讲学科：改用 `audit-live-room-subject-content`，它要求连续音轨、完整本地 ASR 与时间点截图，不能用普通抽帧代替。

## 转写与字幕

- 中文、多语、内部、敏感或长音视频：使用 `local-sota-transcription` 的
  Qwen3-ASR-0.6B 先转写，再释放 ASR 并串行运行 ForcedAligner；只有 0.6B
  关键片段抽检失败时才回退 1.7B。
- 人名、数字、日期、否定词等疑难短片段：用同一 Skill 的本地 whisper.cpp 复核。
- 英文字幕生产、逐字时间轴要直接进入 MG/剪辑：加载 `media-use`；其 Parakeet-MLX 路线必须先通过现场预检，未安装时由该 Skill 回退 whisper.cpp。
- ChatCut 项目内已有素材：加载 `chatcut:transcription`，等待项目转写完成并修复源词，不把外部逐字稿假装成 ChatCut 内部已就绪状态。

## 后续制作

- 使用 Remotion 制作任意人物口播成片：`remotion-talking-head`；必须先完成五版效果图审稿并明确选版，再进入整片制作与发布级 QA。
- 通用说话人视频编辑：ChatCut 的 `talking-head-guide`、`verification` 与 `export`。
- MG、数据动效、透明叠加层：`hyperframes` / `motion-graphics`；需要网页视频工程时再考虑 Remotion。
- Jack 封面：`make-jack-cover`；封面是独立资产，不改源视频。

先用 `watch` 产出的时间戳、帧路径和验证过的逐字稿作为下游证据。只有用户明确要求制作、修改或导出时，才执行后续写入。

## 上游维护

当前帧抽取核心基于 `bradautomates/claude-video` commit
`83da59fa78c3eee9e20f515fe75c438bb5166efd`（MIT）。更新时先在临时目录比较
上游变更，只择取下载、抽帧、去重或安全修复；不得用通用安装器直接覆盖
`~/.codex/skills/watch`，否则会丢失本地 Qwen、中文字幕、Codex 看图与验证门禁。
