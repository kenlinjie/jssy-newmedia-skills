# 小白 AI 环境配置 Skill

让已经装好 WorkBuddy 等本地 AI agent 的用户，说清自己的情况后，由 agent 带着装好 AI 软件、接入钉钉／飞书，并建立能追溯修改记录的 Obsidian 知识库。

支持 **macOS 与 Windows**。不需要先掌握终端命令；有本地执行权限的 agent 负责普通下载安装，扫码、登录、系统授权由用户在官方界面完成。

## 三种配置

| 你的情况 | 安装组合 |
| --- | --- |
| 不能科学上网 | ego(lite) |
| 能科学上网，希望简单用 | ChatGPT ＋ ego(lite) |
| 能科学上网，愿意折腾 Claude | ChatGPT ＋ ego(lite) ＋ Cindy ＋ Claude Code |

**三档都会配置：Obsidian ＋ Git ＋ Obsidian Git 插件。** 然后问你用钉钉、飞书还是两个都用，分别接入并用一次真实读取验证。

已有 WorkBuddy 等能使用本 skill 的 agent 是前提；本 skill 沿用它。第一档不会要求用户先买海外 AI 服务。

## 怎么使用

### 已拿到 ZIP：直接从本地使用

打不开 GitHub 时，由协助者把本 skill 的 ZIP 包通过文件传输交给用户。解压后，找到含 `SKILL.md` 的 `ai-environment-setup` 文件夹，在已有的本地 agent 中选择／允许读取这个目录，再发送：

> 请读取我提供的本地 ai-environment-setup 文件夹里的 SKILL.md，以及它按需引用的本地文件，按这个 skill 帮我配置 AI 工作环境。先检查我的系统、网络和办公平台，再继续操作。

宿主有 skill 导入入口时可导入该文件夹；没有也可以先让 agent 读取本地入口执行。正式安装到宿主 skill 目录时，按宿主当前说明操作，不覆盖同名目录。整个 skill 的读取不需要访问 GitHub，也不必先装 Git。

这是免访问 GitHub 的 skill 导入方式，软件安装和云端 AI 仍需相应网络。第一档软件优先使用可达的官方渠道；如果某个安装包或 Git 插件只托管在 GitHub，可由协助者当次从官方当前发布下载，连同版本、适用系统／架构、来源、查询时间和校验值一并传来。不要把长期保存的旧软件安装包混在 skill ZIP 里，也不使用未知加速站。收到的安装包仍要按 skill 核验，无法重新查询时如实记录版本核验时间，不能声称此刻一定最新。

### 能访问 GitHub：从仓库安装

把下面这句话发给你已安装的本地 agent：

> 请安装并使用 https://github.com/kenlinjie/ai-environment-setup 里的 skill，帮我配置 AI 工作环境。先检查我的 Mac／Windows，再问我网络条件和使用钉钉还是飞书，装好对应软件、Obsidian 和 Git 插件，并验证能用。

宿主支持从文件夹导入 skill 时，也可以在 GitHub 点 **Code → Download ZIP**，解压后导入包含 `SKILL.md` 的目录。没有文件夹导入入口时，让 agent 按其当前支持的 skill 目录安装本仓库；不要覆盖已有同名目录。新开会话或重载后使用 `$ai-environment-setup`。

不能访问 GitHub 的电脑，可由协助者先下载 ZIP 并交给用户本地导入。已经可以读取本 skill 后，配置第一档不要求目标电脑能访问所有海外网站；下载官方软件仍需相应官方下载站可达。

## 怎样避免安装旧版

- 每次运行重新查官方发布渠道，匹配目标系统和芯片架构，不使用文档里写死的版本号。
- 已安装软件先检查现有渠道和更新结果，安装后读回实际版本。
- 正式版、Beta、系统不支持、等待重启分别说明，不把旧兼容版或测试版说成最新正式版。
- 官方没有公开数字版本的产品，跟随当次官方下载入口，并核对应用内更新结果。
- 查询失败或无法验证时如实保留未完成项，不宣称全部配置成功。

带有一个可选的 Python 标准库脚本，**只查发布元数据，不下载安装、不读登录凭据**：

```bash
python3 scripts/resolve_latest.py --products obsidian obsidian-git dws
```

Windows 已有 Python 启动器时可用 `py -3`。没有 Python 的电脑直接由 agent 查询官方页面／API，不必为此额外安装 Python。

## 完成后你会得到

- 本档软件的版本、官方来源与实际可用结果。
- 钉钉／飞书的授权状态，以及哪些读取能力已经验证。
- 一个自己选定位置的 Obsidian 知识库，已启用 Git 插件，能看到首次提交历史。
- 三个后续使用示例：查指定办公文档、保存笔记、查看笔记历史。

Git 默认先做本地版本管理。是否远程备份单独选择，个人知识库建议私有；**开源这个 skill 不等于公开使用者的笔记**。已有库、Git 历史、账号和配置会被保留。

## 文件结构

- [SKILL.md](SKILL.md)：agent 入口与完成标准。
- [references/](references/)：官方下载、Mac、Windows、办公接入、Obsidian Git 的按需步骤。
- [scripts/resolve_latest.py](scripts/resolve_latest.py)：当前官方发布元数据查询。
- [assets/vault.gitignore](assets/vault.gitignore)：新知识库的忽略规则模板。
- [tests/](tests/)：发布查询的行为测试；GitHub Actions 在 Mac／Windows 运行。

## 验证范围

测试覆盖：发布源身份、正式版／预览版区分、LTS 选择、网络／限流失败、未知响应，以及不把元数据查询当安装完成。运行方式：

```bash
python3 -m unittest discover -s tests -v
```

自动化测试不在真实用户电脑上安装应用，也不代替企业授权、GUI 或模型可用性验收。每次使用仍需在目标电脑完成 skill 中的实际检查。

## 许可

[MIT](LICENSE)。本仓库发布的是配置 skill，不分发所提及软件；各软件和服务适用其各自的许可与账号条件。
