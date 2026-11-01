"""Check shipped UI and changed backend bytecode, not just a version label."""
import argparse
import hashlib
import json
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    executable = candidate/'Phrasync.exe'
    archive = CArchiveReader(str(executable)).open_embedded_archive('PYZ.pyz')
    modules = {}
    for module in sorted(name for name in archive.toc if name == 'phrasync' or name.startswith('phrasync.')):
        packaged = archive.extract(module)
        source = ROOT/Path(*module.split('.'))
        source = source/'__init__.py' if source.is_dir() else source.with_suffix('.py')
        expected = compile(source.read_text(encoding='utf-8'), packaged.co_filename, 'exec', dont_inherit=True, optimize=0)
        modules[module] = packaged == expected
    resources = {}
    for source in (ROOT/'static').rglob('*'):
        if not source.is_file():
            continue
        relative = source.relative_to(ROOT/'static')
        shipped = candidate/'_internal/static'/relative
        resources[str(relative)] = shipped.exists() and source.read_bytes() == shipped.read_bytes()
    assert 'phrasync.config' in modules and 'phrasync.webgl_renderer' in modules
    report = {'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
              'backendMatchesSource': modules, 'staticMatchesSource': resources,
              'ok': all(modules.values()) and all(resources.values())}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'ok':report['ok'], 'backend':modules, 'staticResources':len(resources), 'sha256':report['sha256']}))
    assert report['ok'], 'Candidate differs from the tested source'


if __name__ == '__main__':
    main()
