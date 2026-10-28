---
name: agent-reach
description: 检索或读取互联网资料，尤其是需要平台专用 CLI、登录态或通用搜索后备路径时使用。已有可用的专用连接器优先；仅提及平台、链接或加工已提供的内容不触发。
metadata:
  homepage: https://github.com/Panniantong/Agent-Reach
  upstream-version: "1.6.0"
---

# Agent Reach

为当前资料需求选择可用的搜索、网页或平台后端。以实际取得的正文或数据为完成依据。

## 选择与完成

- 用户指定工具时沿用该工具；其他情况优先使用已可用、适合目标的连接器、API 或 CLI。需要浏览器时遵守用户的浏览器偏好。
- 按当前问题选择信源和检索范围。指定文章直接定位并读正文；跨平台比较才扩展平台。证据足以回答时结束检索。
- 当前 Reach 统一 CLI 的调用、输出与错误处理见 [当前 CLI](references/current-cli.md)。`agent-reach channels` 声明动作和参数；配置不明或出现连接、认证错误时再按需运行 `agent-reach doctor --text`，只处理相关平台，不把未实测状态当作后端缺失。
- 失败后依据错误选择一次有信息增益的重试或可用后备路径。成功即停；认证或权限阻塞时明确说明缺失内容，不把摘要、空结果或搜索命中当作全文。
- 资料读取不附带全平台体检、CLI 升级或版本推广。工具维护按用户要求处理。

## 按需参考

| 需要 | 读取 |
|---|---|
| 当前 Reach 统一 CLI | [references/current-cli.md](references/current-cli.md)；声明的平台能力与完整性见 [references/capabilities.md](references/capabilities.md) |
| 网页搜索 | [references/search.md](references/search.md) |
| X、Reddit、小红书、B站等平台内容 | [references/social.md](references/social.md) 的对应平台部分 |
| 网页正文、RSS | [references/web.md](references/web.md) |
| GitHub 仓库或代码 | [references/dev.md](references/dev.md) |
| 招聘、LinkedIn | [references/career.md](references/career.md) |
| 视频、字幕、播客 | [references/video.md](references/video.md) |
| 雪球行情与内容 | [references/finance.md](references/finance.md) |

## 认证和数据

- 复用用户已授权的登录态；不自动读取浏览器 Cookie。需要手动凭据时按对应平台的 Cookie-Editor 流程处理。
- 浏览器仍优先 ego Lite。Reach 某渠道若会启用专用浏览器或自动复制其他浏览器的登录，先使用现有连接器或 ego Lite 的可见页面完成；只有用户明确选择该后端后才按官方说明配置。不把来源更新当成更换浏览器、迁移登录或安装软件的授权。
- 平台 reference 中的专用 CLI 只在实际选择且本机可用时使用；旧版命令不能当作当前 Reach 统一命令。凭据不进入命令回显、日志或交付物。
- 本技能获取资料，不自动发帖、评论、点赞或联系他人。
- 临时抓取输出放 `/tmp/`；交付物按用户指定位置保存。配置数据使用 `~/.agent-reach/`。
