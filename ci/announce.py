#!/usr/bin/env python3
"""post a rich message about a new tele release to the telegram channel."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request


def git(repo, *args):
    return subprocess.run(
        ['git', '-C', repo, *args],
        check=True,
        capture_output=True,
        encoding='utf-8',
    ).stdout


def subject(text):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith('Subject: '):
            continue
        value = line[len('Subject: '):]
        for folded in lines[index + 1:]:
            if not folded.startswith((' ', '\t')):
                break
            value += folded
        value = re.sub(r'^\[PATCH[^\]]*\]\s*', '', value)
        return re.sub(r'^[a-z]+(\([^)]*\))?!?:\s*', '', value)
    return None


def patches(repo, rev):
    result = {}
    names = git(repo, 'ls-tree', '-r', '--name-only', rev, '--', 'patches').split()
    for name in names:
        if not name.endswith('.patch'):
            continue
        text = git(repo, 'show', f'{rev}:{name}')
        # only the changed lines count, so moved context or new blob ids after an upstream bump don't
        changes = '\n'.join(
            line for line in text.splitlines()
            if line.startswith(('+', '-')) and not line.startswith(('+++', '---')))
        result[subject(text) or name] = hashlib.sha256(changes.encode()).hexdigest()
    return result


def previous_patches(repo, rev, tag):
    # a folded queue compares against the previous release folded the same way, so merged patches don't show as dropped
    try:
        baselines = json.loads(git(repo, 'show', f'{rev}:ci/baselines.json'))
    except subprocess.CalledProcessError:
        baselines = {}
    return baselines.get(tag) or patches(repo, tag)


def upstream(repo, rev):
    return git(repo, 'show', f'{rev}:UPSTREAM').strip()


def escape(text):
    text = re.sub(r'([\\`*_\[\]()~=|$!#+\-])', r'\\\1', text)
    return text.replace('<', '&#60;')


def message(args):
    now = patches(args.repo, 'HEAD')
    before = previous_patches(args.repo, 'HEAD', args.previous) if args.previous else {}
    added = [name for name in now if name not in before]
    changed = [name for name in now if name in before and before[name] != now[name]]
    dropped = [name for name in before if name not in now]

    tdesktop = 'https://github.com/telegramdesktop/tdesktop/releases/tag/'
    number = args.tag.rsplit('-tele.', 1)[-1]
    lines = [
        f'## tele for desktop {escape(number)} · {escape(args.upstream.lstrip("v"))}',
        '',
        f'telegram desktop [{escape(args.upstream)}]({tdesktop}{args.upstream}) with {len(now)} patches.',
    ]
    if args.previous:
        was = upstream(args.repo, args.previous)
        if was != args.upstream:
            lines += ['', f'moved from tdesktop {escape(was)} to {escape(args.upstream)}.']
    for title, names in (('new', added), ('changed', changed), ('dropped', dropped)):
        if names:
            lines += ['', f'**{title}**', '']
            lines += [f'- {escape(name)}' for name in names]
    if args.previous and not (added or changed or dropped):
        lines += ['', 'same patches as before.']
    lines += [
        '',
        'builds for windows, linux and macos are in the release. a running tele updates itself within 3 hours.',
        '',
        '<tg-button-row>'
        f'<tg-button type="url" url="{args.url}/releases/tag/{args.tag}">download</tg-button>'
        f'<tg-button type="url" url="{args.url}/blob/main/docs/features.md">all patches</tg-button>'
        '</tg-button-row>',
        '',
        '<footer>#desktop</footer>',
    ]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, help='tele checkout with history and tags')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--previous', default='', help='previous release tag, empty for the first one')
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--url', required=True, help='github url of the tele repo')
    parser.add_argument('--dry-run', action='store_true', help='print the request instead of sending it')
    args = parser.parse_args()

    payload = {
        'chat_id': os.environ.get('CHANNEL', ''),
        'rich_message': {'markdown': message(args)},
    }
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    request = urllib.request.Request(
        f'https://api.telegram.org/bot{os.environ["BOT_TOKEN"]}/sendRichMessage',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        result = json.load(error)
    if not result.get('ok'):
        print(f'::warning::the announcement failed: {result.get("description")}')
        sys.exit(1)
    print(f'announced {args.tag} as message {result["result"]["message_id"]}')


if __name__ == '__main__':
    main()
