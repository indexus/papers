#!/usr/bin/env python3
"""Regenerate and compile the seven current papers with Tectonic.

Run from any directory. --check also rejects non-reproducible checked-in figures.
--legacy compiles the two 2024 archives into a temporary directory, preserving
those historical PDFs byte for byte.
"""
from argparse import ArgumentParser
from pathlib import Path
import hashlib
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
PAPERS = [
    ('00-manifesto', 'indexus-manifesto'),
    ('10-whitepaper', 'indexus-whitepaper'),
    ('20-client', 'indexus-client'),
    ('30-network', 'indexus-network'),
    ('40-economics', 'indexus-4-economics'),
    ('50-properties-and-applications', 'indexus-properties-and-applications'),
    ('60-history-and-authorship', 'indexus-history-and-authorship'),
]
GENERATORS = ['00-manifesto', '10-whitepaper', '20-client', '30-network', '40-economics',
              '50-properties-and-applications', '60-history-and-authorship']
LEGACY = [('client-algorithm', 'indexus-search-algorithm-paper'),
          ('p2p-protocol', 'indexus-p2p-protocol-paper')]


def figures():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder, _ in PAPERS for p in (ROOT / folder / 'figures').glob('*.tikz')}


def compile_paper(folder, name, output=None):
    command = ['tectonic', '--keep-logs']
    if output is not None:
        command += ['--outdir', str(output)]
    command.append(name + '.tex')
    run = subprocess.run(command, cwd=folder, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = (output or folder) / (name + '.log')
    detail = log.read_text(errors='replace') if log.exists() else run.stdout
    overflows = [float(n) for n in re.findall(r'Overfull \\hbox \(([\d.]+)pt', detail)]
    unresolved = re.search(r'(?:Reference|Citation) .+ undefined|There were undefined references', detail)
    if run.returncode or any(n > 2 for n in overflows) or unresolved:
        print(run.stdout, file=sys.stderr)
        raise RuntimeError(f'{name}: build failed, unresolved reference or overflow > 2 pt')
    print(f'{name}: OK ({len(overflows)} overfull boxes)', flush=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--legacy', action='store_true')
    args = parser.parse_args()
    before = figures()
    for folder in GENERATORS:
        subprocess.run([sys.executable, str(ROOT / folder / 'make_figures.py')], check=True)
    if args.check and before != figures():
        raise RuntimeError('Generated figures changed; review and commit the regenerated files')
    for folder, name in PAPERS:
        compile_paper(ROOT / folder, name)
    if args.legacy:
        for folder, name in LEGACY:
            source = ROOT / folder
            if not source.exists():
                source = ROOT.parent / folder
            if not source.exists():
                raise FileNotFoundError(f'Historical source not found: {folder}')
            with tempfile.TemporaryDirectory(prefix='indexus-paper-') as temporary:
                compile_paper(source, name, Path(temporary))


if __name__ == '__main__':
    main()
