# Mac 安装步骤

仅在用户目标电脑是 Mac 时读取。所有版本与安装包以本次 [官方核验](downloads.md) 为准。

## 识别电脑与已有安装

```bash
sw_vers -productVersion
uname -m
sysctl -n hw.optional.arm64
```

第三项可在 Apple Silicon 上识别原生硬件，避免在 Rosetta 下把 `x86_64` 当成 Intel。系统不提供该键时，结合“关于本机”的芯片信息判断，不用缺失输出硬猜。

只查 `/Applications`、用户自己的 `Applications` 和已知安装渠道，不扫描用户全部文件。可用 `/usr/libexec/PlistBuddy` 读取目标 `.app/Contents/Info.plist` 中的 `CFBundleShortVersionString`；Obsidian 还需在“关于”中核对安装器版本。路径与应用名称以真实安装为准。

Mac 的 `/usr/bin/git` 可能只是尚未安装开发者工具的入口。先用 `xcode-select -p`、可用包管理器和已知 Git 路径确认，再运行 `git --version`，避免只做探测就弹出安装窗口。

## 下载与安装

- 优先匹配原生架构；官网只提供 Universal 时使用其明确支持的 Universal 包。核对当前最低系统要求，不把所有 Mac 都当作支持同一安装包。
- 后台下载到本次任务目录。DMG 按厂商的拖拽／安装流程操作，PKG 按官方安装器操作；路径包含空格时完整引用。不自动运行下载目录里的同名旧安装包。
- 需要用户输入系统密码或确认首次打开时，说明具体弹窗并由用户在系统界面完成。不关闭 Gatekeeper、不批量清除隔离属性。
- 已有软件沿用更新渠道；Homebrew 只在已经可用或用户选择该方式时使用。安装器要求关闭正在使用的应用时，先保存工作并由用户处理。

## 通用软件

### Git

先按 [Git 官方 Mac 说明](https://git-scm.com/install/mac) 选择当前维护的发行方式。已有 Homebrew 时，可以查看当前 formula，再执行对应安装或升级：

```bash
brew update
brew info git
brew install git
```

已安装 Homebrew Git 时，最后一步换成 `brew upgrade git`。只安装／更新 Git，不运行全量 `brew upgrade`。没有 Homebrew 时，给用户说明 Homebrew 与 Apple Command Line Tools 两种选择的安装范围；选定后再安装。不要使用已停止维护的旧 Git DMG。

`command -v git` 和 `git --version` 必须指向刚选择的发行版。Apple Command Line Tools 附带 Git 不一定等于上游最新 Git；若选择该渠道，如实标注，不说成最新上游版。

### Obsidian 与 ego(lite)

按各自官网下载页选择当前构建，完成初始启动。Obsidian 转到 [知识库与 Git 配置](obsidian-git.md)。ego(lite) 完成初始设置后，检查现有 agent 是否能发现 `ego-browser`。

Skill 目录因宿主与版本而异。参考 [ego(lite) 的 WorkBuddy 指南](https://www.egolite.ai/document/zh/docs/workbuddy) 和宿主当前设置查找真实目录；不要把另一台电脑的 `~/.workbuddy/skills` 或 `~/.codebuddy/skills` 当作通用事实。缺少时只同步 `ego-browser`，保留已存在目录；需要重载时新开会话或让用户保存后重启宿主，不杀进程。

验证：用当前 agent 的 `ego-browser` 读取一个可访问公开页的标题。浏览器能打开但 agent 无法调用时，仍属于未接通。

## B／C 档增量

### ChatGPT

从 OpenAI 官方文档进入当次 Mac 下载页，检查是否支持此 Mac 的架构与系统。缺少匹配桌面版时，说明限制并让用户选择官方网页方案或暂缓；网页方案不能标记为桌面版已安装。

登录后检查更新并完成一次简短回答。已有 WorkBuddy 继续承担原有工具调用，不把“安装了 ChatGPT”写成“ChatGPT 已能控制 ego(lite)”。若用户要切换执行 agent，需要在新 agent 中另外验证浏览器及办公 CLI。

### Cindy 与 Claude Code（C 档）

1. Cindy 首次安装使用官网当前 Mac 构建，打开后复用用户现有账号、订阅或安全输入的密钥。若是更新当前承载任务的 Cindy，严格执行 [Cindy 更新边界](downloads.md#cindy-更新边界)。
2. 现场读取 [Claude Code 官方安装说明](https://code.claude.com/docs/en/setup)。优先原生安装器；运行前确认它仍是官方推荐方式。当前官方基础命令如下，版本／频道仍以现场文档为准：

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

3. 已有 Claude Code 使用其安装渠道更新，不叠装多个渠道。原生安装通常可用 `claude update`；包管理器安装按其更新机制处理。
4. 用 `claude --version` 和 `claude doctor` 验证，登录由用户在官方流程完成。只修复所需用户 PATH 条目，保留原配置，不导出凭据。
5. 在用户指定的工作目录做一次无写入简短回答。Cindy 中所选模型也需单独回答；有 Cindy 窗口不代表模型已经连通。Cindy 自带某 harness 时先检查已提供的能力，不重复覆盖它管理的运行环境。
