#!/usr/bin/env python3
"""省域技能包的目录、完整性检查、安装与团队打包；仅依赖 Python 标准库。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile
from privacy_check import audit_project, audit_archive

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache'}
IGNORED_FILES = {'.DS_Store', '.env', 'local-config.md'}


def files(root: Path):
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)
        for name in sorted(names):
            if name in IGNORED_FILES or name.endswith(('.pyc', '.pyo')):
                continue
            path = Path(current) / name
            if path.is_symlink():
                raise ValueError(f'技能内不应包含指向包外的软链：{path}')
            if path.is_file():
                yield path


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in files(root):
        relative = path.relative_to(root).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, 'big'))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, 'big'))
        digest.update(content)
    return digest.hexdigest()


def catalog():
    return json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))


def select(args, data):
    entries = data['skills']
    if getattr(args, 'skill', None):
        wanted = set(args.skill)
        unknown = wanted - {x['id'] for x in entries}
        if unknown:
            raise ValueError('目录里没有这些技能：' + '、'.join(sorted(unknown)))
        chosen = [x for x in entries if x['id'] in wanted]
    else:
        profile = getattr(args, 'profile', 'team')
        chosen = [x for x in entries if x['scope'] == 'team' and (profile != 'core' or x.get('core'))]
    by_name = {x['id']: x for x in entries}
    wanted = {x['id'] for x in chosen}
    pending = list(wanted)
    while pending:
        for name in by_name[pending.pop()].get('depends_on', []):
            if name not in by_name:
                raise ValueError(f'清单缺少依赖技能：{name}')
            if name not in wanted:
                wanted.add(name)
                pending.append(name)
    return [x for x in entries if x['id'] in wanted]


def check(data, entries=None):
    entries = data['skills'] if entries is None else entries
    errors = audit_project()
    external_ids = {item['id'] for item in data.get('external_tools', [])}
    for item in entries:
        for dependency in item.get('external_tools', []):
            if dependency not in external_ids:
                errors.append(f"{item['id']}：缺少外部工具入口 {dependency}")
        folder = ROOT / item['path']
        entry = folder / 'SKILL.md'
        if not entry.is_file():
            errors.append(f"{item['id']}：缺 SKILL.md")
            continue
        text = entry.read_text(encoding='utf-8')
        if not re.search(r'^name:\s*[\"\']?' + re.escape(item['id']) + r'[\"\']?\s*$', text, re.M):
            errors.append(f"{item['id']}：frontmatter 名称不一致")
        if not re.search(r'^description:\s*\S', text, re.M):
            errors.append(f"{item['id']}：缺 description")
        if tree_hash(folder) != item['sha256']:
            errors.append(f"{item['id']}：文件与收录清单不一致；修改后更新 catalog.json 的哈希")
        for relative in item.get('required_files', []):
            if not (folder / relative).is_file():
                errors.append(f"{item['id']}：缺依赖文件 {relative}")
        # 只核对入口中明确的相对文件链接，忽略网址、绝对路径和参数化产物。
        prose = re.sub(r'```[\s\S]*?```', '', text)
        prose = re.sub(r'`[^`\n]+`', '', prose)
        for target in re.findall(r'\]\(([^)]+)\)', prose):
            target = target.strip('<>').split('#', 1)[0]
            if not target or target.lower() in {'url', 'xxx.gif'} or ':' in target or target.startswith(('/', '~')):
                continue
            if any(t in target for t in ('<', '>', '{', '}', '*', ' ', '\\')):
                continue
            if not (folder / target).exists():
                errors.append(f"{item['id']}：入口引用不存在 {target}")
    return errors


def install(args, entries):
    home = Path.home()
    destinations = {
        'agents': home / '.agents/skills',
        'codex': Path(os.environ.get('CODEX_HOME', home / '.codex')) / 'skills',
        'claude': home / '.claude/skills',
        'workbuddy': home / '.workbuddy/skills',
    }
    destination = Path(args.directory).expanduser().absolute() if args.directory else destinations[args.target]
    print(f'目标目录：{destination}')
    if not args.apply:
        print('当前为预览；加 --apply 才复制文件。同名技能会保留。')
    copied = skipped = 0
    for item in entries:
        target = destination / item['id']
        if target.exists() or target.is_symlink():
            print(f"保留已有：{item['id']}")
            skipped += 1
            continue
        print(('安装：' if args.apply else '将安装：') + item['id'])
        if args.apply:
            target.mkdir(parents=True, exist_ok=False)
            try:
                source = ROOT / item['path']
                for path in files(source):
                    output = target / path.relative_to(source)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, output)
                template = target / 'local-config.example.md'
                if template.is_file():
                    shutil.copy2(template, target / 'local-config.md')
            except Exception:
                # 清理仅限这次新建的目标，已有技能从不进入此分支。
                shutil.rmtree(target)
                raise
        copied += 1
    print(f"{'已安装' if args.apply else '预计安装'} {copied} 个；保留已有 {skipped} 个。")
    if args.apply:
        print('新开或重载 agent 会话后生效。软件依赖和办公账号按技能现场配置。')


def package(args, data):
    entries = [x for x in data['skills'] if x['scope'] == 'team']
    errors = check(data, entries)
    if errors:
        raise ValueError('\n'.join(errors))
    output = Path(args.output).expanduser().absolute() if args.output else ROOT / 'dist/省域新媒体-skills-团队版.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    portable = {k: v for k, v in data.items() if k != 'skills'}
    portable['skills'] = entries
    prefix = '省域新媒体-skills'
    handle, temporary = tempfile.mkstemp(prefix='.province-package-', suffix='.tmp', dir=output.parent)
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            def add(path, relative):
                archive.write(path, f'{prefix}/{relative}')
            add(ROOT / 'docs/同事上手.md', 'README.md')
            for name in ['AGENTS.md', 'CLAUDE.md', '.gitignore', 'THIRD_PARTY.md', 'scripts/skillpack.py', 'scripts/privacy_check.py', 'docs/同事上手.md']:
                add(ROOT / name, name)
            archive.writestr(f'{prefix}/catalog.json', json.dumps(portable, ensure_ascii=False, indent=2) + '\n')
            for item in entries:
                source = ROOT / item['path']
                for path in files(source):
                    add(path, f"{item['path']}/{path.relative_to(source).as_posix()}")
        privacy_issues = audit_archive(temporary)
        if privacy_issues:
            raise ValueError('\n'.join(privacy_issues))
        Path(temporary).replace(output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(json.dumps({'file': str(output), 'skills': len(entries), 'bytes': output.stat().st_size, 'sha256': digest}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['list', 'check', 'install']:
        command = commands.add_parser(name)
        command.add_argument('--profile', choices=['core', 'team'], default='team')
        command.add_argument('--skill', action='append', help='可多次传入，精确指定技能')
        if name == 'install':
            command.add_argument('--target', choices=['agents', 'codex', 'claude', 'workbuddy'], default='agents')
            command.add_argument('--directory', help='另一个技能目录；优先于 --target')
            command.add_argument('--apply', action='store_true', help='实际复制；不覆盖同名技能')
    commands.add_parser('doctor')
    command = commands.add_parser('package')
    command.add_argument('--output')
    args = parser.parse_args()
    data = catalog()
    if args.command == 'package':
        package(args, data)
    elif args.command == 'doctor':
        for name in ['python3', 'git', 'dws', 'node', 'npm', 'ffmpeg', 'ffprobe', 'uv', 'obsidian', 'ego-browser']:
            print(f"{name}: {shutil.which(name) or '未在 PATH 找到'}")
        print('这只检查本地命令位置，不验证登录、组织权限、模型资源或软件实际可用性。')
    else:
        entries = select(args, data)
        if args.command == 'list':
            for item in entries:
                print(f"{item['category']} | {item['id']} | {item['title']} | {item['scope']}")
            print(f'共 {len(entries)} 个随附技能。')
            for item in data.get('external_tools', []):
                print(f"外部官方工具（按需） | {item['title']} | {item['homepage']}")
        elif args.command == 'check':
            errors = check(data, entries)
            if errors:
                print('\n'.join(errors), file=sys.stderr)
                return 1
            print(f'通过：{len(entries)} 个技能的名称、内容哈希、必需文件和入口链接。')
        elif args.command == 'install':
            errors = check(data, entries)
            if errors:
                raise ValueError('\n'.join(errors))
            install(args, entries)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'未完成：{exc}', file=sys.stderr)
        raise SystemExit(1)
