#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能包本地校验脚本（纯标准库，零依赖）。

对齐 WorkBuddy 技能市场口径，校验生成的技能目录结构与 SKILL.md 字段：
  - SKILL.md 存在且在根目录
  - 九件套必填字段齐全
  - name 为小写字母/数字/连字符（全网唯一需用户自查）；允许中文，但中文仅本地显示用，
    上架 SkillHub 需改回英文（中文记 WARNING 不记 ERROR）
  - category 取 9 选 1 合法值
  - service_category 取 9 选 1 合法值（若存在）
  - examples_zh 与 examples_en 数量一致，且各 ≤ 3
  - description* 建议 ≥ 20 字
  - YAML 铁律：冒号后空格、无 Tab、无中文引号
  - 目录层级 ≤ 2 级，icon 文件存在

退出码：0 全通过；1 存在 ERROR（必须修）；2 仅 WARNING。
缺关键要素时非零退出并打印缺失项（供 SkillHub 上架前自检）。

用法：
    python validate_skill_pack.py <技能目录>
"""
import os
import re
import sys

VALID_CATEGORIES = [
    "生活服务", "开发工具", "投资理财", "内容创作", "数据分析",
    "效率工具", "办公协作", "教育学习", "设计创意",
]
VALID_SERVICE_CATEGORIES = [
    "商业服务", "生活服务", "教育学习", "医疗健康", "金融理财",
    "企业服务", "内容创作", "数字营销", "技术研发",
]
REQUIRED_NINE = [
    "name", "display_name", "display_name_en", "description", "description_zh",
    "description_en", "category", "version", "author",
]
MAX_EXAMPLES = 3
ERRORS, WARNINGS = [], []


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, False
    end = text.find("\n---", 3)
    if end == -1:
        return {}, False
    raw, data, key = text[3:end], {}, None
    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        m_list = re.match(r"^-\s+(.*)$", line.strip())
        if m_list and key:
            if isinstance(data.get(key), list):
                data[key].append(m_list.group(1).strip())
            continue
        m_key = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line.strip())
        if m_key:
            key = m_key.group(1)
            v = m_key.group(2).strip()
            data[key] = [] if v == "" else v.strip("\"'")
    return data, True


def report(code):
    print("=" * 62)
    print("技能包本地校验报告")
    print("=" * 62)
    for e in ERRORS:
        print("[ERROR ] %s" % e)
    for w in WARNINGS:
        print("[WARN  ] %s" % w)
    if not ERRORS and not WARNINGS:
        print("全部通过：九件套齐全、分类与服务类目合法、examples 数量配对合规。")
    print("=" * 62)
    return code


def main():
    if len(sys.argv) < 2:
        print("用法: python validate_skill_pack.py <技能目录>")
        return 1
    base = sys.argv[1]
    if not os.path.isdir(base):
        print("ERROR 目录不存在: %s" % base)
        return 1

    skill_md = os.path.join(base, "SKILL.md")
    if not os.path.isfile(skill_md):
        print("ERROR 根目录缺少 SKILL.md: %s" % base)
        return 1

    text = open(skill_md, "r", encoding="utf-8").read()
    data, ok = parse_frontmatter(text)
    if not ok:
        ERRORS.append("frontmatter 解析失败：文件必须以 --- 开头并以 --- 结尾")
        return report(1)

    # 九件套
    for k in REQUIRED_NINE:
        v = data.get(k)
        if not v or (isinstance(v, list) and not v):
            ERRORS.append("缺少必填字段 %s" % k)

    # name
    name = str(data.get("name", "")).strip()
    if name and re.search(r"[\u4e00-\u9fff]", name):
        WARNINGS.append(
            "name 含中文（当前: %s）：本地技能列表按 name 显示，中文可正常显示；"
            "但上传 SkillHub 前需改为小写英文（目录名保持英文即可，不影响显示）" % name
        )
    elif name and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        ERRORS.append("name 必须是中文或小写字母数字连字符（当前: %s）" % (name or "空"))

    # category
    cat = str(data.get("category", "")).strip()
    if not cat:
        ERRORS.append("category 不能为空")
    elif cat not in VALID_CATEGORIES:
        ERRORS.append("category 非法（当前: %s）；合法取值: %s" % (cat, " / ".join(VALID_CATEGORIES)))
    else:
        print("  OK  category = %s" % cat)

    # service_category
    scat = str(data.get("service_category", "")).strip()
    if scat:
        if scat not in VALID_SERVICE_CATEGORIES:
            ERRORS.append("service_category 非法（当前: %s）；合法取值: %s" % (scat, " / ".join(VALID_SERVICE_CATEGORIES)))
        else:
            print("  OK  service_category = %s" % scat)

    # examples
    zh = data.get("examples_zh") or []
    en = data.get("examples_en") or []
    if not isinstance(zh, list) or not isinstance(en, list):
        ERRORS.append("examples_zh / examples_en 必须是列表")
    else:
        if len(zh) > MAX_EXAMPLES:
            ERRORS.append("examples_zh 最多 %d 个，当前 %d 个" % (MAX_EXAMPLES, len(zh)))
        if len(en) > MAX_EXAMPLES:
            ERRORS.append("examples_en 最多 %d 个，当前 %d 个" % (MAX_EXAMPLES, len(en)))
        if len(zh) != len(en):
            ERRORS.append("examples_zh 与 examples_en 数量必须一致（zh=%d, en=%d）" % (len(zh), len(en)))
        if len(zh) == len(en) and zh and len(zh) <= MAX_EXAMPLES:
            print("  OK  examples 各 %d 个（上限 %d）" % (len(zh), MAX_EXAMPLES))

    # description 长度（建议 ≥20）
    for k in ("description", "description_zh", "description_en"):
        v = str(data.get(k, "")).strip()
        if v and len(v) < 20:
            WARNINGS.append("%s 过短（%d 字），建议 ≥20 字并带上触发词" % (k, len(v)))

    # YAML 铁律
    end = text.find("\n---", 3)
    raw = text[3:end if end != -1 else len(text)]
    for i, line in enumerate(raw.splitlines(), 1):
        if "\t" in line:
            ERRORS.append("第 %d 行含 Tab，YAML 不允许 Tab 缩进（用空格）" % i)
        for q in ("“", "”", "‘", "’"):
            if q in line:
                WARNINGS.append("第 %d 行含中文引号 %s，建议去掉或用「」" % (i, q))
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(.+)$", line)
        if m and not m.group(2).startswith(" "):
            ERRORS.append("第 %d 行冒号后未空格" % i)

    # 目录层级 ≤ 2
    for root, _dirs, files in os.walk(base):
        rel = os.path.relpath(root, base)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        for fn in files:
            if fn == "validate_skill_pack.py":
                continue
            if depth + 1 > 2:
                ERRORS.append("文件层级超过 2 级: %s" % os.path.join(rel, fn))

    # icon 存在
    icon = str(data.get("icon", "")).strip()
    if icon and not os.path.isfile(os.path.join(base, icon)):
        ERRORS.append("icon 声明的 %s 在技能包里不存在" % icon)

    return report(1 if ERRORS else (2 if WARNINGS else 0))


if __name__ == "__main__":
    sys.exit(main())
