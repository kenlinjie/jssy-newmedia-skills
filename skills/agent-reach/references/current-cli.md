# 当前 Reach CLI

本参考依据 Agent Reach 1.6.0 的公开技能与能力声明整理；它不表示使用者电脑已安装此版本。实际可用动作和参数以 `agent-reach channels` 和当前 CLI 帮助为准，命令不存在时报告版本差异，继续使用已可用的连接器或公开读取路径，不自动升级。

## 读取与结果

```bash
agent-reach channels
agent-reach read '<用户提供的链接>'
agent-reach <渠道> <动作> <当前帮助要求的参数>
```

优先已有合适连接器与公开资料。只有 Reach 能补充用户所需内容时才调用，不为普通查询配置全平台。

返回默认是一行 JSON：`ok: true` 的正文在 `items`，原始数据在 `raw`。分别核对正文、评论和字幕是否实际取得，不能把列表、摘要或计数当全文。`ok: false` 时读取 `error.code`、`error.message` 和 `error.hint`。

| 状态 | 处理 |
| --- | --- |
| `BAD_INPUT` / `NOT_FOUND` | 看当前帮助或核对链接，只有新证据支持时才修正重试 |
| `NEED_SETUP` | 说明缺少哪项依赖或配置；安装按用户授权进行 |
| `NEED_LOGIN` / `PLATFORM_BLOCKED` | 暂停该路径，请用户在官方界面完成登录或验证；不索取密码，不换账号绕过 |
| `RATE_LIMITED` / `BUSY` | 保留已有结果，按返回的等待条件或用户操作状态继续，不切换后端反复请求 |
| `TIMEOUT` | 结合失败阶段按需检查 `agent-reach doctor --text`；避免循环重试或开窗 |
| `UPSTREAM_BROKEN` | 说明具体平台当前不可用；有明确版本修复证据且用户授权更新时才升级 |

某渠道会启用专用浏览器时遵守本项目的 ego Lite 优先规则，不能自动迁移 Chrome 登录、清理会话或抢占用户窗口。没有授权的后端只报告缺口，已有公开证据照常交付。

## 能力边界

详见 [上游能力声明](capabilities.md)。例如小红书文字和已加载评论不等于看懂图片或完整评论树；BOSS 编码薪资不能猜数字；YouTube、B 站存在字幕轨道不表示字幕正文已获取。

公开来源：[Agent Reach](https://github.com/Panniantong/Agent-Reach/tree/14c213405669414492bda0f8d52cc6531d062c45/agent_reach/skill)。
