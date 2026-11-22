#!/usr/bin/env python3
"""Check compiled companion-PDF links, named destinations and Markdown targets.

Requires pypdf. Run after build.py. This checks actual PDF actions, including
GoToR destinations, rather than assuming a successful TeX build resolves them.
External websites are not fetched.
"""
from pathlib import Path
import re
from urllib.parse import unquote, urlparse
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
cache = {}


def reader(path):
    path = path.resolve()
    if path not in cache:
        cache[path] = PdfReader(path)
    return cache[path]


def check_destination(pdf, destination):
    if isinstance(destination, str):
        assert destination in pdf.named_destinations, f'Unknown destination: {destination}'
    elif destination and isinstance(destination[0], int):
        assert 0 <= destination[0] < len(pdf.pages), f'Page out of range: {destination[0]}'


def main():
    local = remote = markdown = 0
    for path in sorted(ROOT.glob('[0-9]*/*.pdf')):
        pdf = reader(path)
        for page in pdf.pages:
            for annotation in page.get('/Annots', []):
                action = annotation.get_object().get('/A', {})
                kind = action.get('/S')
                if kind == '/GoTo':
                    check_destination(pdf, action.get('/D'))
                    local += 1
                elif kind == '/GoToR':
                    name = action['/F']
                    if not isinstance(name, str):
                        name = name.get('/UF') or name['/F']
                    target = (path.parent / unquote(name)).resolve()
                    assert target.is_relative_to(ROOT) and target.is_file(), f'Missing PDF: {target}'
                    check_destination(reader(target), action.get('/D'))
                    remote += 1
    for path in [ROOT / 'README.md', *sorted((ROOT / 'ai-transparency').rglob('*.md'))]:
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            url = urlparse(link)
            if url.scheme or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            assert target.is_relative_to(ROOT) and target.is_file(), f'Missing Markdown target: {path.name}: {link}'
            if target.suffix == '.pdf' and url.fragment.startswith('nameddest='):
                check_destination(reader(target), unquote(url.fragment.removeprefix('nameddest=')))
            markdown += 1
    print(f'PDF links: {local} local actions, {remote} companion actions OK; Markdown: {markdown} targets OK')


if __name__ == '__main__':
    main()
