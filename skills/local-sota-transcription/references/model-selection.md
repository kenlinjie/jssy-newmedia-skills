# 模型选择、固定版本与证据边界

## 当前分级链（2026-08-17）

### 0. 系统级极轻量路线

- 引擎：macOS `SpeechAnalyzer` + `SpeechTranscriber`。
- 用途：普通对话、草稿、快速浏览；只在 `supportedLocales` 和
  `installedLocales` 都通过预检时使用。
- 当前机器实测：`zh-CN` 可用、受支持且语言资源已安装。
- 边界：Apple 将它定义为正常对话和一般用途的转写模块，但没有提供与本
  任务 Qwen 中文会议基准可直接比较的数字，因此不能宣称更准。输出的是
  `audioTimeRange` 片段范围，不等于 ForcedAligner 逐词时间戳。

官方资料：

- <https://developer.apple.com/documentation/Speech/SpeechAnalyzer>
- <https://developer.apple.com/documentation/speech/speechtranscriber>
- <https://developer.apple.com/videos/play/wwdc2025/277/>

### 1. 默认正式转写

- ASR：`mlx-community/Qwen3-ASR-0.6B-8bit`，模型页标注约 `1.01 GB`。
- 固定 revision：`89e96d92ba34aca20b3e29fb10cc284097d1219f`。
- `model.safetensors`：`1,006,229,426` 字节；SHA-256
  `b5bfe4abc1b4c6e58b633096682ec2b6297298add1527119936107d211adf0e8`。
- 运行时：`mlx-audio==0.4.6`，独立环境位于
  `~/.local/share/codex-local-asr/venv`。
- 默认仅生成分块级粗时间戳，避免额外常驻一个对齐模型。

官方 Qwen 公开表中，`WenetSpeech meeting` 的 WER（越低越好）为 0.6B
`6.88`、1.7B `5.88`。这说明 0.6B 牺牲一部分会议准确度换取显著更小的模型，
是这台 16 GB Mac 更合理的默认；该表是厂商基准，不能代替用户真实录音抽检。

- <https://github.com/QwenLM/Qwen3-ASR>
- <https://huggingface.co/mlx-community/Qwen3-ASR-0.6B-8bit>

### 2. 按需逐词对齐

- 对齐器：`mlx-community/Qwen3-ForcedAligner-0.6B-8bit`。
- 只在明确需要逐词时间戳或最终字幕时加载。
- 实现必须分成两个阶段：完成 ASR 并保存检查点，释放 ASR 和 MLX 缓存，
  再加载对齐器；不得让 ASR 与对齐器同时常驻。
- 对齐结果仍需抽查零时长、错位和跨分块边界，不能把程序 `passed` 等同于
  人工听辨正确。

- <https://huggingface.co/mlx-community/Qwen3-ForcedAligner-0.6B-8bit>

### 3. 准确度回退与独立复核

- 回退 ASR：保留的 `mlx-community/Qwen3-ASR-1.7B-8bit`，仅用于噪声、
  方言、复杂专名、0.6B 抽检失败的任务或片段。
- 复核：`whisper.cpp 1.9.1` + `ggml-large-v3-turbo-q5_0.bin`，强制
  `--no-gpu`，只跑短片段以保持与 Qwen 架构独立。

1.7B 官方会议 WER 更低，但默认使用会增加模型体积、内存峰值和功耗；所以
保留为有证据触发的回退，不再作为默认主链。

## 未作为当前主链的候选

- `SenseVoiceSmall` 很小，中文、情绪和音频事件能力有吸引力，但当前 Skill
  已有 Qwen 的上下文、长音频检查点和 ForcedAligner 验收链。没有同一批真实
  中文会议的准确度与恢复测试前，不再并装第二套默认运行时。
- Zipformer/WeNet 一类流式模型适合实时字幕，但部署与词表/语言模型组合更多，
  不如系统 SpeechAnalyzer 适合作为本机普通录音的零维护入口。
- `VibeVoice-ASR` 可联合输出说话人、时间和内容，但模型更大，不适合 16 GB
  Mac 的默认稳态。
- `Fun-ASR-Nano` 对中文远场、口音和热词有优势，也能组合 VAD/说话人模型；
  但其时间戳与当前验收链不等价，保留为未来同集对比候选。
- Whisper large-v3-turbo 中文专有名词质量不稳定，但本机已有 CPU 链，适合
  独立复核，不作为数小时主转写。

## 固定与升级

不得自动追随 `main`。升级系统入口、MLX-Audio 或模型时：

1. 新建独立环境或带 revision 的模型目录，不覆盖当前可用版本；
2. 验证仓库、license、revision、权重字节数与 SHA-256；
3. 在同一组真实中文片段比较专有名词、数字、否定词、CER/WER、耗时和峰值；
4. 验证预检、分块恢复、二阶段对齐恢复、源哈希读回和全部输出；
5. 通过后再更新本文件、脚本常量与 `MODEL_SOURCE.json`。
