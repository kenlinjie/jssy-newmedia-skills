# 公众号排版组件库 —— 曜金专业风

近白留白、石墨黑正文与香槟金细线构成的专业编辑风。强调克制、连续阅读与可信感；黑底只用于封面，不在正文反复制造停顿。

## 设计变量速查表

| 项目 | 值 |
|---|---|
| 主色 / 金线 | `#B99655` |
| 背景 | `#FCFBF8` |
| 浅卡底 | `#F7F3EA` |
| 正文 | `#3D3B37` |
| 标题 / 墨黑强调 | `#171717` |
| 装饰线 | `#E6D8BD` |
| 正文下划线 | `border-bottom:1.5px solid #D5B77D;font-weight:700;` |
| 正文字号 | `15px` |

## 各组件完整 HTML

### 1. 全局容器

```html
<section style="max-width:677px;margin:0 auto;background:#FCFBF8;font-family:'Source Han Serif SC','Songti SC','STSong','SimSun',serif;color:#3D3B37;line-height:1.95;letter-spacing:0.35px;overflow-x:hidden;">
  <span leaf="">{{全部内容放在这里}}</span>
</section>
```

### 2. 刊头封面

```html
<section style="margin:18px 10px 28px;padding:24px 20px;background:#171717;border-top:3px solid #B99655;">
  <p style="margin:0;color:#D9C08A;font-size:11px;letter-spacing:2.5px;"><span leaf="">PROFESSIONAL NOTES</span></p>
  <p style="margin:16px 0 8px;color:#FFFFFF;font-size:23px;font-weight:700;line-height:1.45;"><span leaf="">{{文章标题}}</span></p>
  <p style="margin:0;color:#CFC8BA;font-size:13px;line-height:1.7;"><span leaf="">{{副题或阅读引导}}</span></p>
</section>
```

### 3. 摘要与引言

```html
<section style="margin:0 10px 24px;padding:16px 18px;background:#F7F3EA;border-left:3px solid #B99655;">
  <p style="margin:0 0 7px;color:#8C6C35;font-size:11px;letter-spacing:1.8px;"><span leaf="">ABSTRACT</span></p>
  <p style="margin:0;color:#252525;font-size:16px;font-weight:700;"><span leaf="">{{摘要标题}}</span></p>
  <p style="margin:8px 0 0;color:#5B5852;font-size:14px;line-height:1.85;"><span leaf="">{{摘要说明}}</span></p>
</section>
```

### 4. 弱分隔线

```html
<section style="margin:28px 10px 24px;border-top:1px solid #B99655;"><span leaf=""><br></span></section>
```

### 5. 章节标题

```html
<section style="margin:34px 10px 18px;padding-top:10px;border-top:1px solid #B99655;">
  <p style="margin:0;color:#8C6C35;font-size:12px;letter-spacing:2px;"><span leaf="">01／{{ENGLISH TAG}}</span></p>
  <h3 style="margin:5px 0 0;color:#171717;font-size:21px;line-height:1.45;"><span leaf="">{{中文章节标题}}</span></h3>
</section>
```

### 6. 结语标题

```html
<section style="margin:34px 10px 18px;padding-top:10px;border-top:1px solid #B99655;">
  <p style="margin:0;color:#8C6C35;font-size:12px;letter-spacing:2px;"><span leaf="">∞／CLOSING NOTE</span></p>
  <h3 style="margin:5px 0 0;color:#171717;font-size:21px;line-height:1.45;"><span leaf="">{{结语标题}}</span></h3>
</section>
```

### 7. 正文关键词段落

```html
<p style="margin:0 10px 18px;color:#3D3B37;font-size:15px;line-height:1.95;text-align:justify;">
  <span leaf="">{{前文}}</span><span style="border-bottom:1.5px solid #D5B77D;font-weight:700;"><span leaf="">{{关键词}}</span></span><span leaf="">{{后文}}</span>
</p>
```

### 8. 编辑按语

```html
<section style="margin:22px 10px;padding:14px 16px;border-left:3px solid #B99655;background:#F7F3EA;">
  <p style="margin:0;color:#252525;font-size:16px;font-weight:700;line-height:1.85;"><span leaf="">「{{核心金句}}」</span></p>
  <p style="margin:6px 0 0;color:#625D55;font-size:13px;line-height:1.75;"><span leaf="">{{补充说明，可省略}}</span></p>
</section>
```

### 9. 轻量旁注

```html
<section style="margin:20px 10px;padding:12px 16px;border-left:2px solid #CFC2AA;">
  <p style="margin:0;color:#625D55;font-size:14px;line-height:1.85;"><span leaf="">{{旁注内容}}</span></p>
</section>
```

### 10. 递进清单

```html
<section style="margin:22px 10px;padding:15px 16px;border-top:1px solid #B99655;border-bottom:1px solid #E6D8BD;">
  <p style="margin:0 0 9px;color:#8C6C35;font-size:11px;letter-spacing:1.5px;"><span leaf="">ARGUMENT LINE</span></p>
  <p style="margin:7px 0;color:#302E2A;font-size:14px;"><span leaf="">01　{{第一点}}</span></p>
  <p style="margin:7px 0;color:#302E2A;font-size:14px;"><span leaf="">02　{{第二点}}</span></p>
  <p style="margin:7px 0;color:#302E2A;font-size:14px;"><span leaf="">03　{{第三点}}</span></p>
</section>
```

### 11. 延伸阅读与签名

```html
<section style="margin:24px 10px;padding:16px;background:#F7F3EA;">
  <p style="margin:0;color:#8C6C35;font-size:11px;letter-spacing:1.5px;"><span leaf="">FURTHER READING</span></p>
  <p style="margin:8px 0 0;color:#252525;font-size:14px;"><span leaf="">{{延伸阅读标题}}</span></p>
</section>
<section style="margin:24px 10px 34px;padding:16px;text-align:center;border-top:1px solid #E6D8BD;">
  <p style="margin:0;color:#8C6C35;font-size:11px;letter-spacing:1.8px;"><span leaf="">AUTHOR NOTE</span></p>
  <p style="margin:8px 0 0;color:#252525;font-size:14px;line-height:1.8;"><span leaf="">我是 AI交付局。</span></p>
  <p style="margin:6px 0 0;color:#625D55;font-size:13px;line-height:1.8;"><span leaf="">如果这篇内容带来启发，欢迎点赞、在看、转发。</span></p>
</section>
```

## 完整文章模板骨架

`全局容器 → 刊头封面 → 摘要 → 连续正文 → 仅在论点转折处使用章节标题 → 一处编辑按语 → 结语标题 → 延伸阅读 → 作者签名`。

本主题默认不用目录、数据卡或高对比观点卡。它优先让正文连续展开，金线只承担轻量定位。

## 文章类型 → 组件组合配方表

| 类型 | 核心组件 | 点缀 |
|---|---|---|
| 观点 / 深度分析 | 封面、摘要、连续正文、编辑按语 | 章节标题、递进清单（最多一次） |
| 科技评论 | 封面、连续正文、章节标题 | 轻量旁注、代码块 |
| 随笔 / 叙事 | 摘要、连续正文、结语 | 编辑按语（最多一次） |
| 研究解读 | 摘要、章节标题、连续正文 | 递进清单、旁注 |

## Markdown → 组件映射规则表

| Markdown 元素 | 对应组件 |
|---|---|
| `# 标题` | 刊头封面；公众号平台标题另设 |
| `## 标题` | 章节标题；末章用结语标题 |
| `### 标题` | 轻量旁注式小标题 |
| 普通段落 | 正文关键词段落，每段一处金线标记 |
| 核心金句 / 引用 | 编辑按语，全文最多一次 |
| 并列论点 | 递进清单，全文最多一次 |
| 图片 | 通用图片组件，保持最大宽度自适应 |
| 代码块 | 通用深色代码块 |
| 文末 | 延伸阅读与签名 |
