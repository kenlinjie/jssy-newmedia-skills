# Windows 安装步骤

仅在用户目标电脑是 Windows 时读取。默认走原生 Windows 与 PowerShell，不为了本任务额外安装 WSL。

## 识别系统与现有工具

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture
[System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
Get-Command git, node, npm, npx, winget, dws, lark-cli, claude -ErrorAction SilentlyContinue | Select-Object Name, CommandType, Source
```

`OSArchitecture` 用来识别原生 x64／ARM64；不要只看当前 PowerShell 进程的位数。若旧 PowerShell 不支持该类型，结合 `$env:PROCESSOR_ARCHITEW6432`、`$env:PROCESSOR_ARCHITECTURE` 及“设置 → 系统 → 关于”核对。

确认命令属于原生 Windows，避免把 WSL 里的 Git 或 Node 当成 Windows 应用可调用的工具。路径通过 `Join-Path` 等方式构造；包含中文与空格的路径要完整引用。

## 安装与更新

- 从当次官方下载页选择当前匹配的 EXE／MSI／MSIX／商店渠道，按官网明确支持判断 ARM64、x64 和系统版本。官方称 Universal 时也须核对支持范围。
- 使用后台 HTTP 下载或关闭浏览器自动打开下载文件；文件落盘后先核对来源与签名，再开始安装。需要管理员密码时由用户在系统弹窗处理。
- WinGet 已可用时，可通过 `winget show --id <官方核对的ID> --exact` 查看版本、来源与安装器。确认来源及版本匹配后再安装；包列表落后于官网时不能把它当最新版。已有软件沿用其安装来源更新。
- 不更改整个电脑的 ExecutionPolicy，不关闭 Defender／SmartScreen。被策略阻止时按报错给出官方受支持安装方式或管理员处理条件。
- 新安装命令后重开终端／重载当前进程 PATH，必要时让用户保存后重开 agent；不要求小白手动猜安装路径。

## Git、Obsidian 与 ego(lite)

1. 按 [Git 官网 Windows 入口](https://git-scm.com/install/windows) 安装当前 Git for Windows，采用允许第三方软件调用 Git 的 PATH 选项和默认凭据管理器。装 GitHub Desktop 不能替代系统 Git。
2. WinGet ID 若当次核对仍是 `Git.Git`，可以从该包安装／更新；安装后用原生 `git --version` 验证。保留既有凭据与 Git 全局配置。
3. 安装当前 Obsidian，启动后选择正确知识库，再按 [知识库与 Git 配置](obsidian-git.md) 启用插件。终端能运行 Git 但插件找不到时，根据当前插件设置指定已确认的 Git 可执行文件；不改整台机器的 Git 配置。
4. ego(lite) 使用 [Windows 官方入门](https://www.egolite.ai/document/zh/docs/windows/quick-start)。如果当前官方只提供 Beta，先告知并由用户选择，再继续；测试版不能标成正式版。
5. 完成 ego(lite) 初始设置，在实际 agent 的 skill 列表检查 `ego-browser`。读取宿主当前安装说明确定用户级 skill 目录；现有目录先比较，不覆盖。必要时只同步这一个 skill 并重载会话。
6. 通过当前 agent 调用 ego(lite) 读取一个可访问的公开页标题。调用后关闭本任务自己的 Space／会话，不影响其他任务和用户标签页。

## B／C 档增量

### ChatGPT

使用 [OpenAI Windows 官方文档](https://learn.chatgpt.com/docs/app/windows) 当次指向的下载或 Microsoft Store 入口，核对产品发布者、系统与架构要求。仅在电脑实际支持且安装完成后标记“已安装”。

企业商店策略、账号条件或系统版本阻止安装时，说明具体原因。用户选择官方网页作为替代时保留替代标识；不能说桌面版安装成功。引导登录、更新检查和一次回答。

### Cindy（C 档）

从 [官网下载页](https://cindy.app/download) 读取当前 Windows 支持和构建。官网只提供 x64 时，不把它写成原生 ARM64；兼容运行需有官方明确支持并取得用户选择。按安装器完成首次安装并验证所选模型可回答。

更新承载当前任务的已有 Cindy 时，执行 [Cindy 更新边界](downloads.md#cindy-更新边界)，使用内置更新器。

### Claude Code（C 档）

1. 读取 [Claude Code 当前官方安装说明](https://code.claude.com/docs/en/setup)，先检查已有安装及频道；优先原生 Windows 安装器。当前官方基础命令为：

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```

   这是 PowerShell 命令，不能让小白直接粘进 CMD。执行前仍需现场核对官方推荐方式。

2. 已安装时按原安装渠道更新；原生安装可检查 `claude update`，WinGet 安装按官方包 ID 更新。避免原生版、npm 版、WSL 版同时叠装造成命令指向旧版。
3. 原生 Git for Windows 已由通用步骤配置。若当前官方仍需要额外 shell 配置，用其当次文档处理；不要无条件要求装 WSL 或按旧教程写死 `CLAUDE_CODE_GIT_BASH_PATH`。
4. 新终端检查 `claude --version`、`claude doctor`。缺 PATH 时只补实际安装目录，不覆盖已有 PATH。
5. 用户按官方流程认证后，验证一次无写入回答。安装成功但没账号或模型不可用时，保留“已安装，待认证／模型接通”。

## npm 类 CLI 的前置条件

只有选中的办公 CLI 需要而电脑缺少时，才安装当前 Node.js LTS。用 `node --version`、`npm --version`、`npx --version` 确认当前进程可用。

遇到 `npm.ps1`／`npx.ps1` 被策略限制时，可在官方安装支持的前提下调用同一安装目录的 `npm.cmd`／`npx.cmd`，不靠关闭系统策略解决。企业代理和证书错误按企业提供的配置处理，不禁用 TLS 校验。
