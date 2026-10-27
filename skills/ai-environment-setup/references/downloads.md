# 官方下载与版本核验

这里保存官方入口和核验方式，不保存可直接沿用的版本快照。每次安装时重新获取。

## 通用规则

1. 先列本档实际需要的软件，只查询这些项目。对用户不能访问的海外服务，不反复测试，也不替用户改代理、DNS、证书或系统防护。
2. 查询最新正式发布的版本／频道，确认目标系统和原生架构有安装包。跟随官方下载页实际链接，校验最终域名、文件类型和发布者；不能用搜索广告、第三方“高速下载”或猜测的 CDN 路径。
3. 有校验和或系统签名就校验；下载到任务目录，防止浏览器自动打开。保留来源、查询时间和目标版本，下载不成功不算安装成功。
4. 只有通过系统兼容性检查后才安装。复用安装渠道更新已有应用；包管理器版本落后时不能直接说“最新”。不为追新自动升级用户的整个操作系统或其他项目依赖。
5. 安装后读回版本，并完成应用内更新检查／CLI 更新状态核验。若源站在过程中又发布新版，按新的官方结果更新目标。
6. 官方网站没有公开数字版本时，记录当次官方下载入口及应用内更新检查结果，允许这种证据；仅“我刚从官网下载了”不足以证明已更新。

“已查到发布版本”“已下载”“已安装”“已验证可用”是不同状态。旧系统只能安装兼容旧版时，说明新版本不兼容，由用户选择后才能装兼容版，并清楚标注。

## GitHub 不可达时

已通过 ZIP 导入的本地 skill 可以直接使用，不要反复访问仓库、重新克隆或要求用户先装 Git。先检查当前产品是否有厂商自己维护且可访问的下载站／国内发布源，例如 DWS 的官方 Gitee。不能因为官网能打开，就假设其背后的 GitHub 安装包也能下载。

某项软件的官方安装包或插件资产仅托管在不可达的 GitHub 时，可由协助者当次代下载并传给用户：

- 仍从本次查到的官方当前发布取得，匹配目标电脑的系统和原生架构。
- 随文件提供原始官方来源、发布版本／频道、查询时间、文件名及大小。厂商有签名／官方校验和时一并提供并验证；另算传输用 SHA-256，区分“传输未损坏”和“厂商来源已验证”。
- 先核对用户收到的文件与上述资料，再安装。插件还需检查 manifest 中的版本与 `minAppVersion`。
- 文件版本过旧、不匹配系统、缺来源证据时不安装；等待取得正确官方文件。对方只给一个无来源的“最新版压缩包”不能作为依据。
- 目标电脑无法再联网核验当前版本时，如实写“官方版本于某时核验，当前最新性待在线复核”，不能把代下载时间说成永远最新。

只分发 skill 时不捆绑应用安装包，避免软件版本过时或架构混用。不自动上传到第三方镜像、网盘或创建额外公开仓库；有明确分发指令时再处理相应平台。

## 产品入口与特殊处理

| 产品 | 官方入口 | 获取当前版本与验证方式 |
| --- | --- | --- |
| ego(lite) | [下载](https://www.egolite.ai/download)、[Mac 入门](https://www.egolite.ai/document/zh/docs/quick-start)、[Windows 入门](https://www.egolite.ai/document/zh/docs/windows/quick-start) | 当次页面的系统／架构、发布标签及当前安装包；安装后查看版本与更新结果。以当次页面判断 Windows 是否仍是 Beta。 |
| ChatGPT | [OpenAI 官方桌面文档](https://learn.chatgpt.com/docs/app)、[Windows 文档](https://learn.chatgpt.com/docs/app/windows) | 从官方文档当次给出的下载／商店入口进入；核对系统要求、安装后版本和更新结果。不把 Codex 独立安装包当作 ChatGPT。 |
| Cindy | [官网下载页](https://cindy.app/download)、[源码](https://github.com/makecindy/cindy) | 官网动态加载的当前官方构建及架构；用应用内更新器核验。GitHub 源码 tag 不一定对应桌面发布，不能从 tag 猜二进制下载地址。 |
| Claude Code | [安装与更新](https://code.claude.com/docs/en/setup)、[认证](https://code.claude.com/docs/en/authentication) | 优先官方原生安装／更新方式，现场核对 `latest` 与 `stable` 的含义；`claude --version`、官方更新结果和 `claude doctor`。默认取当前最新正式发布频道，不锁定旧版本。 |
| Obsidian | [下载](https://obsidian.md/download)、[更新说明](https://obsidian.md/help/updates)、[官方发布](https://github.com/obsidianmd/obsidian-releases/releases/latest) | 以官网下载页标出的当前公开版为准；区分应用版本和安装器版本，不能只更新应用而一直留下旧安装器。禁用 Insider／Catalyst 作为默认安装目标。 |
| Git | [官网安装入口](https://git-scm.com/install/)、[Mac](https://git-scm.com/install/mac)、[Windows](https://git-scm.com/install/windows) | 核对目标平台的当前发行版并读回 `git --version`。Apple Git、Homebrew Git 和 Git for Windows 的版本标识不同，要写清发行渠道。 |
| Obsidian Git | [插件主页](https://github.com/Vinzent03/obsidian-git)、[安装说明](https://publish.obsidian.md/git-doc/Installation)、[正式发布](https://github.com/Vinzent03/obsidian-git/releases/latest) | 社区插件里的 Git，插件 ID 为 `obsidian-git`。核对作者／仓库、发布版本、插件 manifest 的 `minAppVersion`、实际启用状态。 |
| 钉钉 DWS | [CLI 官方站](https://open.dingtalk.com/dingtalk-cli)、[官方命令参考](https://open.dingtalk.com/dingtalk-dev/wiki) | 国内优先直接打开官方站，安装、授权和官方技能接入以当次官网为准；版本与实际读取在安装后核验。 |
| 飞书 CLI | [飞书团队官方仓库](https://github.com/larksuite/cli)、[开放平台](https://open.feishu.cn/) | 核对官方说明、npm `@larksuite/cli` 的 `latest`，按当前官方安装器获取 `lark-cli`，读回 CLI 版本。不要混用同名第三方 CLI。 |
| Node.js（仅缺少且需要时） | [官网](https://nodejs.org/en/download)、[官方发布索引](https://nodejs.org/dist/index.json) | 先检查现有 Node／npm 是否满足目标 CLI 的当前要求。需要新装时选最新受支持 LTS，匹配系统和架构；LTS 不等于 Current。 |

### Cindy 更新边界

首次安装另一台电脑上的 Cindy：从官网下载当前匹配构建，按系统步骤引导。

若正在更新承载本任务的 Cindy：发现 `cindy_helper` 能力后使用 `install_app_update`；`check_app_update` 只读版本，不等于安装。安装器返回无更新或不支持时转告原因；工具不可用时，引导在运行 Cindy 的电脑上进入“设置 → 检查更新”。这类已有 Cindy 更新不通过 shell 下载替换应用、杀进程、重启应用或注册持久任务完成。

### ChatGPT 与 Claude 的账号条件

网络能访问不代表账号已满足产品或地区条件。安装后引导用户在官方界面登录，真实验证一次回答。ChatGPT 的订阅、API 额度、Claude Code 的订阅／API 凭据分别核对，不互相假定，不自动下单。

## 可选发布查询脚本

脚本只用 Python 标准库，没有依赖安装；它不读用户凭据、不执行安装脚本、不修改配置，也不缓存旧版本。

```bash
# 在本 skill 根目录，有 Python 3.9+ 时运行。只选择本次需要的产品。
python3 scripts/resolve_latest.py --products obsidian obsidian-git dws
```

Windows 的 Python 启动器可用时：

```powershell
py -3 scripts/resolve_latest.py --products obsidian obsidian-git feishu
```

输出含查询时间、产品、发布源、目标版本、当前发布 API 给出的资产或包信息。`release_metadata` 只说明取得了发布元数据，不保证安装包支持目标系统，也不证明本机已安装。按官方页面逐项检查兼容性。

`needs_official_page` 表示该产品需从官方页面／内置更新器核对，脚本不会猜版本。失败返回 `error`。HTTP 403／限流等失败不能读旧缓存充数；转向同一厂商可访问的官方入口，不使用未验证镜像。

Python 报 `CERTIFICATE_VERIFY_FAILED` 时，检查当前 Python 的可信证书配置；可使用系统／企业已信任的 CA，或改用能正常验证证书的宿主 HTTP 工具读取同一官方来源。不要关闭 TLS 校验，也不要因此把最新版本标记为已核验。

退出码：`0`＝所选元数据均已获取；`2`＝还有页面核验项；`1`＝至少一项错误。三种退出码都不表示环境配置已完成。
