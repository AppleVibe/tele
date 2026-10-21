#!/usr/bin/env python3
"""write the github release notes for a tele release as markdown, and optionally as json for the app."""

import argparse
import json
import posixpath
import re
import subprocess

from announce import git, patches, previous_patches, subject, upstream

SOURCES = ('docs/releases.md', 'README.md')
ROW = re.compile(r'^\| \[(\d+)\]\((?:\.\./)?(patches/[^)]+\.patch)\) \| (.*) \| (.*) \|$')
LINK = re.compile(r'\]\((?![a-z][a-z0-9+.-]*:)([^)\s]+)\)')

PLATFORMS = (
    ('windows', 'win64.zip', 'unpack anywhere and run `tele.exe`.'),
    ('linux', 'linux64.zip', 'unpack and run `tele`. it adds itself to the app menu on the first start.'),
    ('macos', 'macos.dmg', 'open it, drag tele into applications and run `xattr -dr com.apple.quarantine /Applications/tele.app` once: the build is signed ad-hoc.'),
)


def rooted(text, source):
    folder = posixpath.dirname(source)

    def fix(match):
        target = match.group(1)
        if target.startswith('#'):
            return f']({source}{target})'
        return f']({posixpath.normpath(posixpath.join(folder, target))})'

    return LINK.sub(fix, text)


def release_lines(repo, rev):
    for source in SOURCES:
        try:
            text = git(repo, 'show', f'{rev}:{source}')
        except subprocess.CalledProcessError:
            continue
        return rooted(text, source).splitlines()
    return []


def parse_rows(lines):
    rows = {}
    for line in lines:
        match = ROW.match(line.strip())
        if match:
            number, path, what, where = match.groups()
            rows[path] = (int(number), what, where)
    return rows


def release_rows(repo, rev):
    return parse_rows(release_lines(repo, rev))


def paths_by_subject(repo, rev):
    result = {}
    names = git(repo, 'ls-tree', '-r', '--name-only', rev, '--', 'patches').split()
    for name in names:
        if name.endswith('.patch'):
            result[subject(git(repo, 'show', f'{rev}:{name}')) or name] = name
    return result


def absolute(text, url, rev):
    return LINK.sub(lambda m: f']({url}/blob/{rev}/{m.group(1)})', text)


def entry(rows, path, fallback, url, rev):
    if path in rows:
        number, what, where = rows[path]
        return f'- {absolute(what, url, rev)} ([{number}]({url}/blob/{rev}/{path}), {where})'
    return f'- {fallback}'


def plain(text):
    return re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text).replace('`', '')


def changes(args):
    now = patches(args.repo, args.rev)
    before = previous_patches(args.repo, args.rev, args.previous) if args.previous else {}
    paths = paths_by_subject(args.repo, args.rev)
    rows = release_rows(args.repo, args.rev)
    added = [name for name in now if name not in before]
    changed = [name for name in now if name in before and before[name] != now[name]]
    dropped = [name for name in before if name not in now]
    return now, paths, rows, added, changed, dropped


CATEGORIES = ('interface', 'chats', 'messages', 'sending', 'notifications', 'menus', 'privacy',
              'profiles and ids', 'bots', 'server', 'backup', 'updates', 'debug', 'everywhere', 'other')


def category(where, wheres, seen=()):
    where = plain(where).strip().lower()
    related = re.match(r'with (\d+)', where)
    if related:
        number = int(related.group(1))
        return category(wheres[number], wheres, (*seen, number)) if number in wheres and number not in seen else 'other'
    if where.startswith('always on'):
        return 'everywhere'
    place = re.match(r'tele → ([^,→]+)', where)
    name = place.group(1).strip() if place else ''
    return name if name in CATEGORIES else 'other'


def app_where(where, wheres, seen=()):
    where = plain(where).strip()
    related = re.match(r'with (\d+)', where, re.I)
    if related:
        number = int(related.group(1))
        if number not in wheres or number in seen:
            return ''
        return re.sub(r',\s*(on|off)\b.*$', '', app_where(wheres[number], wheres, (*seen, number)))
    return re.sub(r'\s*\((see|with) \d+\)|,\s*(see|with) \d+', '', where).strip()


def changelog(args):
    _, paths, rows, added, changed, _ = changes(args)
    wheres = {number: where for number, _, where in rows.values()}
    items = []
    for name in added + changed:
        path = paths.get(name, '')
        if path in rows:
            _, what, where = rows[path]
            item = {'text': plain(what), 'where': app_where(where, wheres), 'category': category(where, wheres)}
        else:
            item = {'text': name, 'where': '', 'category': 'other'}
        item['url'] = f'{args.url}/blob/{args.rev}/{path}' if path else ''
        items.append(item)
    present = {item['category'] for item in items}
    return {
        'tag': args.tag,
        'title': f"tele {args.tag.rsplit('-tele.', 1)[-1]}",
        'categories': [name for name in CATEGORIES if name in present],
        'items': items,
        'url': f'{args.url}/releases/tag/{args.tag}',
    }


def notes(args):
    rev = args.rev
    now, paths, rows, added, changed, dropped = changes(args)

    tdesktop = f'https://github.com/telegramdesktop/tdesktop/releases/tag/{args.upstream}'
    lines = [f'telegram desktop [{args.upstream}]({tdesktop}) with {len(now)} patches.']
    if args.previous:
        was = upstream(args.repo, args.previous)
        if was != args.upstream:
            lines += ['', f'moved from tdesktop {was} to {args.upstream}.']
    sections = (
        ('new', [entry(rows, paths.get(name, ''), name, args.url, rev) for name in added]),
        ('changed', [entry(rows, paths.get(name, ''), name, args.url, rev) for name in changed]),
        ('dropped', [f'- {name}' for name in dropped]),
    )
    for title, items in sections:
        if items:
            lines += ['', f'## {title}', '', *items]
    if args.previous and not (added or changed or dropped):
        lines += ['', 'same patches as before, rebuilt.']

    download = f'{args.url}/releases/download/{args.tag}'
    lines += ['', '## download', '', '| system | file | |', '|---|---|---|']
    for name, platform, how in PLATFORMS:
        file = f'tele-{args.tag}-{platform}'
        lines.append(f'| {name} | [{file}]({download}/{file}) | {how} |')
    lines += [
        '',
        'a running tele finds this release within 3 hours and offers a restart, or right away with settings → tele → check for updates.',
    ]

    table = [
        f'| [{number}]({args.url}/blob/{rev}/{path}) | {absolute(what, args.url, rev)} | {where} |'
        for path, (number, what, where) in sorted(rows.items(), key=lambda item: item[1][0])
    ]
    summary = '\n'.join(lines) + '\n'
    if table:
        lines += [
            '',
            '<details>',
            f'<summary>all {len(now)} patches</summary>',
            '',
            '| # | what it does | where to toggle |',
            '|---|---|---|',
            *table,
            '',
            '</details>',
        ]
    result = '\n'.join(lines) + '\n'
    if len(result) > 120000:
        return summary + f'\n[All {len(now)} patches]({args.url}/blob/{rev}/docs/releases.md)\n'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, help='tele checkout with history and tags')
    parser.add_argument('--rev', default='HEAD', help='commit the release is built from')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--previous', default='', help='previous release tag, empty for the first one')
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--url', required=True, help='github url of the tele repo')
    parser.add_argument('--out', required=True, help='file to write the markdown to')
    parser.add_argument('--json', default='', help='file to write the changelog json for the app to')
    args = parser.parse_args()
    with open(args.out, 'w', encoding='utf-8', newline='\n') as file:
        file.write(notes(args))
    if args.json:
        with open(args.json, 'w', encoding='utf-8', newline='\n') as file:
            json.dump(changelog(args), file, ensure_ascii=False, indent=2)
            file.write('\n')


if __name__ == '__main__':
    main()
