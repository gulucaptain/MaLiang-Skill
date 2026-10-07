#!/usr/bin/env python3
"""File-based, code-only bridge to MaLiang's registered capabilities; no model loop."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

LOCAL_HARNESS = '/Users/zhaohaoyu/Documents/05_Code/Davinci'


def read_json(path):
    with open(path, encoding='utf-8') as stream:
        return json.load(stream)


def portable(value, store):
    """Remove image payloads, decode evidence text, add host-readable paths."""
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict) and item.get('type') in ('image_url', 'image'):
                continue
            if isinstance(item, dict) and item.get('type') == 'text':
                try:
                    item = json.loads(item['text'])
                except (ValueError, KeyError):
                    pass
            result.append(portable(item, store))
        return result
    if isinstance(value, dict):
        result = {k: portable(v, store) for k, v in value.items()}
        if isinstance(value.get('paths'), list):
            result['absolute_paths'] = [str(store.path(p)) for p in value['paths']]
        return result
    return value


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--harness', default=os.environ.get('MALIANG_HARNESS_ROOT', LOCAL_HARNESS))
    p.add_argument('--python', default=os.environ.get('MALIANG_PYTHON'))
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    init = sub.add_parser('init')
    init.add_argument('project')
    init.add_argument('--spec-file', required=True, help='Artwork JSON; bridge enforces guided/code-only')
    init.add_argument('--budget-file', help='Budget JSON, persisted across bridge calls')
    edit = sub.add_parser('edit')
    edit.add_argument('project', help='Source project')
    edit.add_argument('target')
    edit.add_argument('--revision', type=int, required=True)
    edit.add_argument('--instruction-file', required=True)
    edit.add_argument('--budget-file')
    for name in ('state', 'verify', 'versions'):
        sub.add_parser(name).add_argument('project')
    schemas = sub.add_parser('schemas')
    schemas.add_argument('project')
    schemas.add_argument('--tool', help='Return only this capability schema')
    call = sub.add_parser('call')
    call.add_argument('project')
    call.add_argument('tool')
    call.add_argument('--args-file', required=True, help='UTF-8 JSON object, avoiding inline shell quoting')
    return p


def execute(args):
    root = Path(args.harness).expanduser().resolve()
    if not (root / 'src/davinci/agent.py').is_file():
        raise ValueError('Harness source not found; set --harness or MALIANG_HARNESS_ROOT')
    sys.path.insert(0, str(root / 'src'))
    if args.command == 'doctor':
        modules = ['deepagents', 'langchain_openai', 'langgraph.checkpoint.sqlite',
                   'pydantic', 'PIL', 'av', 'playwright', 'filelock']
        missing = []
        for name in modules:
            try:
                present = importlib.util.find_spec(name) is not None
            except ModuleNotFoundError:
                present = False
            if not present:
                missing.append(name)
        result = {'harness': str(root), 'python': sys.executable, 'missing_dependencies': missing,
                  'code_only': True, 'host_visual_input_required': True,
                  'host_model_usage_metered': False, 'renderer_execution': 'unverified'}
        if not missing:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                chromium = Path(os.environ.get('DAVINCI_CHROMIUM', pw.chromium.executable_path))
                if not chromium.is_file() and 'DAVINCI_CHROMIUM' not in os.environ:
                    local_chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
                    if local_chrome.is_file():
                        chromium = local_chrome
                result['chromium'] = str(chromium)
                result['chromium_exists'] = chromium.is_file()
        return result, bool(missing or not result.get('chromium_exists'))
    from filelock import FileLock
    from davinci.models import Artwork, Budget
    from davinci.store import ProjectStore, atomic_json
    project = Path(args.project).expanduser().resolve()
    if args.command != 'init' and not (project / 'artwork.json').is_file():
        raise ValueError('No initialized project at requested path')
    project.mkdir(parents=True, exist_ok=True)
    with FileLock(str(project / '.skill.lock'), timeout=0):
        store = ProjectStore(project)
        config_path = store.path('skill-runtime.json')
        if args.command == 'init':
            data = read_json(args.spec_file)
            if data.get('allow_generated_assets'):
                raise ValueError('This bridge is code-only; generated assets are not supported')
            data.update(workflow_policy='guided', allow_generated_assets=False)
            if not data.get('requirements'):
                raise ValueError('Provide concrete requirements derived from the user brief')
            art = Artwork.model_validate(data)
            if art.revision != 0 or art.program or art.assets or art.objects:
                raise ValueError('init needs a fresh brief; use the edit command for existing artwork')
            budget = Budget.model_validate(read_json(args.budget_file) if args.budget_file else {})
            store.create(art)
            atomic_json(config_path, {'budget': budget.model_dump(), 'mode': 'external-agent-code-only'})
            return {'project': str(project), 'revision': art.revision}, False
        if args.command == 'versions':
            from davinci.editing import version_index
            return {'project': str(project), 'versions': version_index(store)}, False
        if 'DAVINCI_CHROMIUM' not in os.environ:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                if not Path(pw.chromium.executable_path).is_file():
                    local_chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
                    if local_chrome.is_file():
                        os.environ['DAVINCI_CHROMIUM'] = str(local_chrome)
        if args.command == 'edit':
            from davinci.editing import create_edit
            target_path = Path(args.target).expanduser().resolve()
            if target_path == project or target_path.is_relative_to(project):
                raise ValueError('Use a separate target directory outside the source project')
            budget = Budget.model_validate(read_json(args.budget_file) if args.budget_file else {})
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with FileLock(str(target_path.parent / ('.' + target_path.name + '.skill-edit.lock')), timeout=0):
                target = ProjectStore(target_path)
                instruction = Path(args.instruction_file).read_text(encoding='utf-8')
                art = create_edit(store, target, args.revision, instruction, preview=True)
                atomic_json(target.path('skill-runtime.json'), {'budget': budget.model_dump(),
                            'mode': 'external-agent-code-only'})
            return {'project': str(target.root), 'revision': art.revision,
                    'source_project': str(project), 'source_revision': args.revision}, False
        from davinci.agent import make_context
        from davinci.settings import ImageGenerationSettings
        config = read_json(config_path) if config_path.exists() else {}
        budget = Budget.model_validate(config.get('budget', {}))
        # Disable extension discovery and neural APIs in this first-version bridge.
        context = make_context(project, budget=budget, resume=True, plugins=False,
                               image_generation=ImageGenerationSettings(enabled=False))
        try:
            if args.command == 'schemas':
                entries = context.registry.describe()
                if args.tool:
                    entries = [entry for entry in entries if entry['name'] == args.tool]
                    if not entries:
                        raise ValueError('Unknown capability')
                result = {'tools': entries, 'backends': context.renderers.available()}
            elif args.command == 'verify':
                from davinci.verification import verify
                result = verify(store)
            else:
                name = 'read_artwork' if args.command == 'state' else args.tool
                arguments = {} if args.command == 'state' else read_json(args.args_file)
                if not isinstance(arguments, dict):
                    raise ValueError('Tool arguments must be a JSON object')
                result = context.registry.invoke(name, arguments)
            failed = isinstance(result, dict) and result.get('status') in ('error', 'needs_revision')
            return {'project': str(project), 'current_revision': store.load().revision,
                    'result': portable(result, store)}, failed
        finally:
            context.meter.flush()


def main():
    args = parser().parse_args()
    root = Path(args.harness).expanduser().resolve()
    bundled = Path(__file__).resolve().parents[2] / '.venv/bin/python'
    candidates = [root / '.venv/bin/python', bundled]
    interpreter = args.python or next((str(p) for p in candidates if p.is_file()), sys.executable)
    if not args.worker:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(root / 'src') + os.pathsep + env.get('PYTHONPATH', '')
        process = subprocess.run([interpreter, str(Path(__file__).resolve()), '--worker', *sys.argv[1:]], env=env)
        return process.returncode
    try:
        result, failed = execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return int(failed)
    except Exception as exc:
        # Avoid traceback / environment dumps; registered tool errors remain in their trace.
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
