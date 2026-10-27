# 网页搜索

使用当前可用的搜索能力定位目标资料。需要 Exa 时：

```bash
mcporter call exa.web_search_exa query="query" numResults=5
```

结果用于定位原文；需要正文时继续读取实际页面。已知精确 URL 时参见 [web.md](web.md)，GitHub 仓库和代码搜索参见 [dev.md](dev.md)。

Exa 限流、超时或无结果时，使用已可用的通用搜索工具；也可用以下公开搜索后备命令：

```bash
opencli yahoo search "query" -f json
```

仅在桥接错误需要诊断时运行 `opencli doctor`。搜索成功后结束后备链；不要为普通资料读取升级工具或要求新增 API Key。

Exa 的 `get_code_context_exa` 已弃用，当前代码问题使用 `web_search_exa` 或 GitHub 专用搜索。
