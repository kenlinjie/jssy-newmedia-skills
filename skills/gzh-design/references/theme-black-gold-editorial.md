# 公众号排版组件库 —— 黑金刊

> 白底留白、墨黑刊头与暗金细线构成的编辑风主题。适用于思想随笔、深度观点与科技评论。所有样式内联，文字节点均用 `<span leaf="">` 包裹。

## 设计变量速查表

| 项目 | 值 |
|---|---|
| 主色 / 金线 | `#B78A3B` |
| 近白背景 | `#FCFBF8` |
| 浅卡底 | `#F7F3EA` |
| 正文色 | `#242424` |
| 墨黑强调 | `#171717` |
| 装饰线 | `#D8C8A7` |
| 正文下划线 | `border-bottom:1.5px solid #D8C8A7;font-weight:600;` |
| 正文字号 | `15px` |

## 组件

### 1. 全局容器

```html
<section style="max-width:677px;margin:0 auto;background:#FCFBF8;font-family:Georgia,'Songti SC','STSong','SimSun',serif;color:#242424;line-height:1.9;letter-spacing:0.4px;overflow-x:hidden;">
  <span leaf="">{{全部内容放在这里}}</span>
</section>
```

### 2. 封面刊头

```html
<section style="margin:0 10px 24px;background:#171717;padding:28px 22px;border-top:4px solid #B78A3B;">
  <p style="margin:0;color:#B78A3B;font-size:12px;letter-spacing:2px;"><span leaf="">EDITORIAL／THOUGHTS</span></p>
  <p style="margin:18px 0 8px;color:#FFFFFF;font-size:22px;font-weight:700;line-height:1.45;"><span leaf="">{{文章标题}}</span></p>
  <p style="margin:0;color:#D8D1C5;font-size:13px;"><span leaf="">{{副题或阅读引导}}</span></p>
</section>
```

### 3. 头版摘要

```html
<section style="margin:0 10px 26px;padding:16px;border:1px solid #D8C8A7;background:#FFFFFF;">
  <p style="margin:0 0 6px;color:#B78A3B;font-size:12px;letter-spacing:1.5px;"><span leaf="">FEATURE</span></p>
  <p style="margin:0;color:#171717;font-size:16px;font-weight:700;"><span leaf="">{{摘要标题}}</span></p>
  <p style="margin:8px 0 0;color:#555555;font-size:14px;line-height:1.8;"><span leaf="">{{摘要说明}}</span></p>
</section>
```

### 4. 栏目索引

```html
<section style="margin:0 10px 30px;padding:10px 12px;background:#F7F3EA;color:#171717;font-size:13px;">
  <p style="margin:0 0 5px;color:#B78A3B;font-weight:700;"><span leaf="">CONTENTS</span></p>
  <p style="margin:0;"><span leaf="">01 {{看点一}}　02 {{看点二}}　03 {{看点三}}</span></p>
</section>
```

### 5. 章节标题

```html
<section style="margin:36px 10px 18px;border-top:1px solid #B78A3B;padding-top:10px;">
  <p style="margin:0;color:#B78A3B;font-size:13px;letter-spacing:2px;"><span leaf="">01／{{ENGLISH TAG}}</span></p>
  <h3 style="margin:4px 0 0;color:#171717;font-size:21px;line-height:1.45;"><span leaf="">{{中文章节标题}}</span></h3>
</section>
```

### 6. 结语标题

```html
<section style="margin:36px 10px 18px;border-top:1px solid #B78A3B;padding-top:10px;">
  <p style="margin:0;color:#B78A3B;font-size:13px;letter-spacing:2px;"><span leaf="">∞／THE END</span></p>
  <h3 style="margin:4px 0 0;color:#171717;font-size:21px;line-height:1.45;"><span leaf="">{{结语标题}}</span></h3>
</section>
```

### 7. 小节标题

```html
<p style="margin:24px 10px 10px;color:#171717;font-size:17px;font-weight:700;border-left:3px solid #B78A3B;padding-left:10px;line-height:1.5;"><span leaf="">{{小节标题}}</span></p>
```

### 8. 正文段落与关键词

```html
<p style="margin:0 10px 18px;font-size:15px;line-height:1.9;text-align:justify;"><span leaf="">{{前文}}</span><span style="border-bottom:1.5px solid #D8C8A7;font-weight:600;"><span leaf="">{{关键词}}</span></span><span leaf="">{{后文}}</span></p>
```

### 9. 编辑按语 / 金句

```html
<section style="margin:20px 10px;padding:14px 16px;background:#F7F3EA;border-left:3px solid #B78A3B;">
  <p style="margin:0;color:#171717;font-size:16px;font-weight:700;line-height:1.8;"><span leaf="">「{{核心金句}}」</span></p>
  <p style="margin:6px 0 0;color:#6D675C;font-size:13px;line-height:1.7;"><span leaf="">{{补充说明，可省略此段}}</span></p>
</section>
```

### 10. 轻量旁注

```html
<section style="margin:20px 10px;padding:12px 14px;border-left:3px solid #8A7A5C;background:#F7F3EA;">
  <p style="margin:0;color:#6D675C;font-size:14px;line-height:1.8;"><span leaf="">{{旁注内容}}</span></p>
</section>
```

### 11. 概念卡

```html
<section style="margin:20px 10px;padding:16px;border:1px solid #D8C8A7;background:#FFFFFF;">
  <p style="margin:0 0 6px;color:#B78A3B;font-size:12px;letter-spacing:1.5px;"><span leaf="">FEATURE</span></p>
  <p style="margin:0;color:#171717;font-size:16px;font-weight:700;"><span leaf="">{{概念标题}}</span></p>
  <p style="margin:8px 0 0;color:#555555;font-size:14px;line-height:1.8;"><span leaf="">{{概念说明}}</span></p>
</section>
```

### 12. 三段论 / 递进清单

```html
<section style="margin:20px 10px;padding:14px 16px;border-top:1px solid #D8C8A7;border-bottom:1px solid #D8C8A7;">
  <p style="margin:0 0 8px;color:#B78A3B;font-size:12px;letter-spacing:1.5px;"><span leaf="">THOUGHT LINE</span></p>
  <p style="margin:7px 0;color:#171717;font-size:14px;"><span leaf="">01　{{第一点}}</span></p>
  <p style="margin:7px 0;color:#171717;font-size:14px;"><span leaf="">02　{{第二点}}</span></p>
  <p style="margin:7px 0;color:#171717;font-size:14px;"><span leaf="">03　{{第三点}}</span></p>
</section>
```

### 13. 对照卡

```html
<section style="margin:20px 10px;padding:14px;border:1px solid #D8C8A7;">
  <p style="margin:0;color:#B78A3B;font-size:13px;"><span leaf="">{{观察}}</span></p>
  <p style="margin:6px 0;color:#171717;font-size:15px;"><span leaf="">{{解释}}</span></p>
  <section style="height:1px;background:#D8C8A7;margin:10px 0;"><span leaf=""><br></span></section>
  <p style="margin:0;color:#B78A3B;font-size:13px;"><span leaf="">{{另一种观察}}</span></p>
  <p style="margin:6px 0 0;color:#171717;font-size:15px;"><span leaf="">{{另一种解释}}</span></p>
</section>
```

### 14. 黑底观点卡

```html
<section style="margin:20px 10px;padding:18px;background:#171717;">
  <p style="margin:0;color:#B78A3B;font-size:12px;letter-spacing:1.5px;"><span leaf="">KEY IDEA</span></p>
  <p style="margin:7px 0 0;color:#FFFFFF;font-size:17px;font-weight:700;line-height:1.75;"><span leaf="">{{关键判断}}</span></p>
</section>
```

### 15. 图片组件

```html
<section style="margin:20px 10px;text-align:center;">
  <span leaf=""><img src="{{图片URL}}" alt="{{图片说明}}" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>
  <p style="margin:7px 0 0;color:#777777;font-size:12px;"><span leaf="">{{图片说明}}</span></p>
</section>
```

### 16. 深色代码块

```html
<section style="margin:20px 10px;padding:14px 16px;background:#171717;">
  <p style="margin:0;color:#B78A3B;font-size:12px;letter-spacing:1px;"><span leaf="">CODE／PROMPT</span></p>
  <p style="margin:8px 0 0;color:#FFFFFF;font-family:monospace;font-size:13px;line-height:1.6;"><span leaf="">{{代码内容}}</span></p>
</section>
```

### 17. 延伸阅读

```html
<section style="margin:24px 10px;padding:12px;background:#F7F3EA;">
  <p style="margin:0;color:#B78A3B;font-size:12px;letter-spacing:1.5px;"><span leaf="">FURTHER READING</span></p>
  <p style="margin:8px 0 0;color:#171717;font-size:14px;"><span leaf="">{{延伸阅读标题}}</span></p>
</section>
```

### 18. 作者签名

```html
<section style="margin:28px 10px 0;padding:16px;text-align:center;background:#F7F3EA;">
  <p style="margin:0;color:#B78A3B;font-size:12px;letter-spacing:2px;"><span leaf="">THE END</span></p>
  <p style="margin:8px 0 0;color:#171717;font-size:14px;line-height:1.8;"><span leaf="">我是 {{作者名}}，{{简介}}。</span></p>
  <p style="margin:8px 0 0;color:#6D675C;font-size:13px;line-height:1.8;"><span leaf="">如果这篇文章带来一点启发，欢迎点赞、在看、转发。</span></p>
</section>
```

## 完整文章模板骨架

`全局容器 → 封面刊头 → 头版摘要 → 栏目索引 → 编号章节（正文／金句／概念卡）→ 结语标题 → 延伸阅读 → 作者签名`。刊头与黑底观点卡仅用于开场和全文不超过 2 处的锚点，正文保持近白底与大留白。

## 文章类型 → 组件组合配方表

| 类型 | 核心组件 | 点缀 |
|---|---|---|
| 观点 / 深度分析 | 封面刊头、章节标题、正文、编辑按语 | 概念卡、对照卡、黑底观点卡 |
| 科技评论 | 封面刊头、正文、概念卡 | 深色代码块、递进清单 |
| 随笔 / 叙事 | 头版摘要、正文、编辑按语 | 轻量旁注、延伸阅读 |
| 教程 / 清单 | 章节标题、递进清单、正文 | 深色代码块、概念卡 |

## Markdown → 组件映射规则表

| Markdown 元素 | 对应组件 |
|---|---|
| `# 标题` | 封面刊头；公众号平台标题另设 |
| `## 标题` | 章节标题，按顺序编号；末章用结语标题 |
| `### 标题` | 小节标题 |
| 普通段落 | 正文段落，每段 1～3 个金线关键词 |
| 核心金句 / 引用 | 编辑按语 / 金句 |
| 并列论点 | 三段论 / 递进清单或对照卡 |
| `**加粗**` | `font-weight:700`；最强判断可用黑底观点卡 |
| `==高亮==` | 概念卡中的金色标签或金线关键词 |
| 图片 | 图片组件 |
| 代码块 | 深色代码块 |
| 文末 | 延伸阅读 + 作者签名 |
