#!/usr/bin/env python3
"""Verify excerpt integrity; optionally compare selected on-device source records.

No database is changed. Source bodies are never printed. See METHOD.md for
retrieval coverage, the optional ChatGPT capture format and the meaning of hashes.
"""
from argparse import ArgumentParser
from pathlib import Path
import hashlib
import json
import re
import sqlite3

ROOT = Path(__file__).resolve().parent
HOME = Path.home()


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def content_text(content):
    if isinstance(content, str):
        return content
    return '\n'.join(x.get('text', '') for x in content or [] if x.get('type') == 'text')


def read_only(path, immutable=False):
    suffix = '?mode=ro&immutable=1' if immutable else '?mode=ro'
    return sqlite3.connect(path.as_uri() + suffix, uri=True, timeout=2)


def varint(data, offset):
    value = shift = 0
    while offset < len(data) and shift <= 63:
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
        shift += 7
    raise ValueError('Invalid protobuf varint')


def fields(data):
    offset = 0
    while offset < len(data):
        tag, offset = varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ValueError('Invalid protobuf field')
        if wire == 0:
            value, offset = varint(data, offset)
        elif wire == 2:
            size, offset = varint(data, offset)
            value = data[offset:offset + size]
            offset += size
        elif wire in (1, 5):
            size = 8 if wire == 1 else 4
            value = data[offset:offset + size]
            offset += size
        else:
            raise ValueError('Unsupported protobuf wire type')
        if offset > len(data):
            raise ValueError('Truncated protobuf field')
        yield number, wire, value


def first_bytes(data, number):
    return next(value for field, wire, value in fields(data) if field == number and wire == 2)


def source_text(q, capture):
    platform, tid, mid = q['platform'], q['thread_id'], q['message_id']
    if not re.fullmatch(r'[0-9a-f-]{36}', tid):
        raise ValueError('Invalid source conversation ID')
    if platform == 'Codex':
        with read_only(HOME / '.codex/thread_history_1.sqlite') as db:
            row = db.execute('select item_type,item_json from thread_items where thread_id=? and item_id=?', (tid, mid)).fetchone()
        expected = 'userMessage' if q['role'] == 'user' else 'agentMessage'
        if not row or row[0] != expected:
            raise LookupError('Source role or message missing')
        msg = json.loads(row[1])
        return msg.get('text') or content_text(msg.get('content'))
    if platform == 'Cursor':
        path = HOME / 'Library/Application Support/Cursor/User/globalStorage/state.vscdb'
        with read_only(path) as db:
            header = db.execute('select value from composerHeaders where composerId=?', (tid,)).fetchone()
            if not header or json.loads(header[0]).get('subagentInfo'):
                raise LookupError('Expected parent conversation')
            row = db.execute('select value from cursorDiskKV where key=?', (f'bubbleId:{tid}:{mid}',)).fetchone()
        msg = json.loads(row[0])
        if msg.get('type') != (1 if q['role'] == 'user' else 2):
            raise LookupError('Source role mismatch')
        return msg['text']
    if platform == 'Claude Code':
        paths = list((HOME / '.claude/projects').glob(f'*/{tid}.jsonl'))
        if len(paths) != 1:
            raise LookupError('Source session unavailable or ambiguous')
        with paths[0].open() as stream:
            for line in stream:
                msg = json.loads(line)
                if msg.get('uuid') == mid:
                    if msg.get('type') != q['role']:
                        raise LookupError('Source role mismatch')
                    return content_text(msg.get('message', {}).get('content'))
        raise LookupError('Source message unavailable')
    if platform == 'Antigravity':
        path = HOME / '.gemini/antigravity/conversations' / (tid + '.db')
        with read_only(path, immutable=True) as db:
            row = db.execute('select step_type,step_payload from steps where idx=?', (int(mid),)).fetchone()
        expected, outer, inner = (14, 19, 2) if q['role'] == 'user' else (15, 20, 1)
        if not row or row[0] != expected:
            raise LookupError('Source role mismatch')
        # Read only the selected visible-text field; never reasoning or tools.
        return first_bytes(first_bytes(row[1], outer), inner).decode('utf-8')
    if platform == 'ChatGPT' and capture:
        conversation = next(c for c in capture if c['id'] == tid)
        for turn in conversation['turns']:
            for msg in turn['items']:
                if msg['id'] == mid:
                    expected = 'userMessage' if q['role'] == 'user' else 'agentMessage'
                    if msg['type'] != expected:
                        raise LookupError('Source role mismatch')
                    return msg.get('text') or content_text(msg.get('content'))
        raise LookupError('Source message unavailable')
    raise LookupError('External history capture not supplied')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--local-sources', action='store_true')
    parser.add_argument('--chatgpt-capture', type=Path)
    args = parser.parse_args()
    excerpts = json.loads((ROOT / 'excerpts.json').read_text())['excerpts']
    episodes = json.loads((ROOT / 'episodes.json').read_text())
    assert excerpts and episodes, 'An empty catalogue is not a successful verification'
    ids = [q['id'] for q in excerpts]
    assert len(ids) == len(set(ids)), 'Duplicate excerpt ID'
    for q in excerpts:
        assert digest(q['text']) == q['excerpt_sha256'], q['id']
        assert q['end_character'] - q['start_character'] == len(q['text']), q['id']
        assert q['role'] in ('user', 'assistant'), q['id']
    assigned = [item for ep in episodes for item in ep['excerpt_ids']]
    assert sorted(assigned) == sorted(ids), 'Every excerpt must belong to one episode'
    for ep in episodes:
        assert (ROOT / 'episodes' / ep['file']).is_file(), ep['file']
    print(f'Integrity: {len(excerpts)} exact excerpt strings and {len(episodes)} episode records OK')
    if not args.local_sources and not args.chatgpt_capture:
        return
    capture = json.loads(args.chatgpt_capture.read_text()) if args.chatgpt_capture else None
    checked = unavailable = failures = not_requested = 0
    for q in excerpts:
        if (q['platform'] == 'ChatGPT' and not capture) or (q['platform'] != 'ChatGPT' and not args.local_sources):
            not_requested += 1
            continue
        try:
            text = source_text(q, capture)
            assert digest(text) == q['source_text_sha256']
            assert text[q['start_character']:q['end_character']] == q['text']
            checked += 1
        except (OSError, LookupError, sqlite3.Error) as error:
            print(f'{q["id"]}: source unavailable ({type(error).__name__})')
            unavailable += 1
        except (AssertionError, ValueError, TypeError, StopIteration):
            print(f'{q["id"]}: source comparison FAILED')
            failures += 1
    print(f'Source comparison: {checked} matched; {not_requested} not requested; {unavailable} unavailable; {failures} mismatches')
    if failures or unavailable:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
