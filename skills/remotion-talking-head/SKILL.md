---
name: remotion-talking-head
description: "Use when the user asks to edit, finish, style, or add visual material to any speech-led or talking-head video with Remotion. Analyze the actual content, create five content-specific visual mockups for approval (three adapted from verifiably popular online templates and two original image-generation concepts), then build and QA a reusable Remotion project only after explicit style selection. Do not use for script-only writing or videos without a speech-led A-roll."
---

# Remotion 口播成片

把任意人物的口播、访谈独白、课程讲解或视频播客 A-roll 做成可继续编辑的 Remotion 成片。默认只依据当前素材，不假定人物是 Jack，也不读取或写入任何人物专属口播 profile，除非用户在当前任务中明确要求。

## 选版门槛

这是硬停止点。没有明确选版，不得渲染整片。

- 先基于视频内容和真实画面做 **5 张不同视觉方向的效果图**，不是五个文字描述或模板网页截图。
- A–C：从网上找到 3 个可证明热门的模板/视觉参考，再用当前视频的代表帧和真实观点重做成效果图。
- D–E：使用图像生成做 2 个原创参考方向；两版必须在构图机制、材质或动势上真正不同，不能只是换颜色。
- 同时提交五图联系表和来源说明。用户修改某版时，只更新审稿素材并再次等待。
- 只有用户明确说出方案编号、名称，或明确指向“就用这版”，才算通过。普通的“可以”“继续看看”或未指明对象的认可不算选版。
- 紧急、自动执行或“先跑起来”不代表可以跳过。只有用户在当前任务中明确说“跳过五版审稿”时，才允许绕过。

选版前允许创建分析文件、代表帧、五张效果图和联系表；不允许输出完整成片或把旧风格直接套满全片。

## 1. 先理解视频

1. 盘点源视频、SRT/转写、目标平台、比例和期望时长。源媒体只读，记录绝对路径和 SHA-256；不覆盖、不移动、不改名。
2. 有 SRT 就优先使用；没有时优先本地转写，未经允许不把声音或逐字稿上传云端。
3. 建立内容地图：开场钩子、核心判断、数字/比较、转折、结论、CTA，以及适合图形或 B-roll 的语义落点。
4. 提取 3–5 张代表帧，标出脸、头发、手势、原字幕、现有包装和平台 UI 风险区。安全距离只约束新增元素；不要因为“留安全区”而擅自把整条 A-roll 缩进黑框。

完成标准：`01-analysis/CONTENT_MAP.md` 已覆盖整条内容逻辑，代表帧能说明主体和字幕占位，源文件哈希已记录。

## 2. 生成五版效果图并停下

完整读取 [references/style-review-gate.md](references/style-review-gate.md)，按其中标准完成热门模板检索、五版差异化设计和审稿包。

- 网上检索必须调用 `agent-reach`；需要浏览器验证时优先 ego Lite，失败后才用 Chrome。
- 两个原创方向必须调用 `imagegen`。生图只作为设计参考，不能替换最终 A-roll，也不能把生成的人脸直接带入成片。
- 五版都要使用当前视频的代表帧、真实标题/数字或观点，保持目标比例。
- 输出 A–E 五张全尺寸 PNG、一个联系表和 `02-style-review/STYLE_REVIEW.md`，然后向用户展示并停止。

完成标准：A–E 五张效果图都能独立评审；A–C 各有直达来源和热门证据；D–E 标明为原创生图参考；没有整片渲染。

## 3. 选版后制作 Remotion 工程

用户明确选版后，完整读取 [references/remotion-production.md](references/remotion-production.md)。

1. 用 `scripts/init_project.py` 建立隔离项目包；已有用户目录时适配现有结构，但保留同等的分析、审稿、Remotion、渲染和 QA 分层。
2. 加载 `remotion:remotion-best-practices` 及其当前任务需要的创建、标记、多媒体和渲染分支。
3. 把选中的视觉语言锁定为本期样式，只沿用其色彩、字阶、构图和运动逻辑；不同语义可以有不同图形机制，不要把同一张卡片重复十几次。
4. 先渲染选中风格的代表帧做内部一致性检查，再实现全片。若实现结果与已批准效果图发生明显偏移，回到审稿门槛，不得自行换风格。
5. 保留所有 JSX/TSX、字体、静态素材、时间点、配置和依赖锁文件，使用户能在 Remotion Studio 继续修改。

完成标准：`03-remotion/` 可独立安装、预览和渲染；源文件仍只读；最终时间轴的每个新增视觉落点都与语义和已批准风格一致。

## 4. 最终验收与交付

完整读取 [references/qa-delivery.md](references/qa-delivery.md)，只从正式 MP4 做验收。

完成标准：最终 MP4、可复用 Remotion 工程、选版审稿包、项目清单、最终联系表和 QA 报告都存在；源文件哈希回读一致。任何一项缺失时不得声称“完成”或“可直接发布”。

## 项目包

默认保留以下结构；不要只留下 MP4：

```text
<project>/
├── 00-source/          # 只保存源路径、哈希和媒体信息，不挪动原片
├── 01-analysis/        # 内容地图、转写引用、代表帧和安全区判断
├── 02-style-review/    # A–E 效果图、联系表、来源与选版记录
├── 03-remotion/        # 完整 Remotion 工程、字体、素材、锁文件
├── 04-renders/         # preview/ 与 final/，版本化且不覆盖旧版
├── 05-qa/              # 最终 MP4 抽帧、日志和 QA_REPORT.md
└── project.json        # 源、平台、选版、版本和交付状态
```

模板作为视觉参考使用。付费模板、字体、音乐或库存素材在没有授权/许可证时不得下载后直接嵌入；可以重建其抽象视觉机制，但不能把未授权资源打包交付。
