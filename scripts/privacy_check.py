#!/usr/bin/env python3
"""检查共享项目与压缩包；只报告规则和文件位置，不回显敏感内容。"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', 'dist', 'node_modules', '.venv', '__pycache__', '.pytest_cache'}
PRIVATE_DIRS = {'.local', 'local-skills', 'voice-profiles', 'private-profiles'}
BINARY_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.pdf', '.mp4', '.mp3', '.wav', '.zip'}
RULES = {
    '个人设备绝对路径': re.compile(r'(?:/Users/|/home/)[A-Za-z0-9_.-]+|[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+'),
    '真实群标识': re.compile(r'cid\+[A-Za-z0-9+/]{18,}={0,2}'),
    '私钥内容': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    '访问凭据': re.compile(r'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9_-]{32,}'),
}


def policy(root=ROOT):
    # 临时传入当前任务需要排除的名称，绝不将这些名称或其指纹保存到共享项目。
    return {'markers': [x.casefold() for x in os.environ.get('SKILLPACK_PRIVATE_MARKERS', '').splitlines() if x]}


def private_text(text, rules):
    lowered = text.casefold()
    return any(marker in lowered for marker in rules['markers'])


def inspect_content(name, content, rules):
    found = []
    normalized = name.replace('\\', '/')
    label = '[文件名已隐藏]' if private_text(normalized, rules) else normalized
    if private_text(normalized, rules):
        found.append(f'{label}：私有名称')
    if set(normalized.split('/')) & PRIVATE_DIRS:
        found.append(f'{label}：私人目录')
    base = normalized.rsplit('/', 1)[-1]
    if base == '.env' or (base.startswith('.env.') and not base.endswith(('.example', '.sample', '.template'))):
        found.append(f'{label}：环境凭据文件')
    if Path(base).suffix.lower() in BINARY_SUFFIXES:
        return found
    text = content.decode('utf-8', errors='replace')
    if private_text(text, rules):
        found.append(f'{label}：私有名称或个人标识')
    for title, regex in RULES.items():
        if regex.search(text):
            found.append(f'{label}：{title}')
    return found


def audit_paths(paths, root=ROOT):
    rules = policy(root)
    issues = []
    for path in paths:
        path = Path(path)
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            issues.append(f'{name}：分发文件不应是外部软链')
            continue
        issues.extend(inspect_content(name, path.read_bytes(), rules))
    return sorted(set(issues))


def project_paths(root=ROOT):
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (Path(current) / d).is_symlink()]
        for name in names:
            if name == '.DS_Store' or name.endswith(('.pyc', '.pyo')):
                continue
            path = Path(current) / name
            if path.is_file() and path.suffix.lower() != '.zip':
                yield path


def audit_project(root=ROOT):
    issues = audit_paths(project_paths(root), root)
    for name in PRIVATE_DIRS:
        if (root / name).exists():
            issues.append(f'{name}：共享项目不应保留私人资料目录')
    return sorted(set(issues))


def audit_archive(path, root=ROOT):
    rules = policy(root)
    issues = []
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            issues.append('压缩包完整性错误')
        for member in archive.infolist():
            if member.is_dir():
                continue
            if member.filename.endswith('/local-config.md'):
                issues.append('压缩包：包含个人状态文件')
            issues.extend(inspect_content(member.filename, archive.read(member), rules))
    return sorted(set(issues))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    issues = audit_archive(args.archive) if args.archive else audit_project()
    if issues:
        print('\n'.join(issues), file=sys.stderr)
        return 1
    print('通过：未发现规则覆盖的个人路径、群标识、凭据或临时指定的私有标识。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
