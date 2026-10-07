#!/usr/bin/env python3
"""Offline bridge integration fixtures, not an LLM quality evaluation.

Requires an installed Harness and Chromium. Creates isolated temporary projects.
Reviews are scripted fixtures; never reuse them as assessments of real user artwork.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--harness', required=True)
    p.add_argument('--python', required=True)
    args = p.parse_args()
    root = Path(tempfile.mkdtemp(prefix='maliang-skill-smoke-'))
    bridge = Path(__file__).with_name('harness.py')
    prefix = [sys.executable, str(bridge), '--harness', args.harness, '--python', args.python]
    checks = []
    counter = 0

    def invoke(*command, expected=0):
        proc = subprocess.run(prefix + list(map(str, command)), capture_output=True, text=True)
        try:
            value = json.loads(proc.stdout)
        except ValueError:
            raise AssertionError(f'Invalid JSON: {proc.stdout[:500]} {proc.stderr[-1000:]}')
        if proc.returncode != expected:
            raise AssertionError(f'{command[0]} failed: {value} {proc.stderr[-1000:]}')
        return value

    def write(value):
        nonlocal counter
        counter += 1
        path = root / f'arguments-{counter}.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def call(project, name, value=None, expected=0):
        response = invoke('call', project, name, '--args-file', write(value or {}), expected=expected)
        return response['result'], response['current_revision']

    def requirements(project):
        return invoke('state', project)['result']['requirements']

    def plan(project):
        current = invoke('state', project)['current_revision']
        reqs = requirements(project)
        result, revision = call(project, 'plan_creation', {
            'expected_revision': current, 'backend': 'scene2d',
            'capability_assessment': 'Fixture: independent 2D shapes and keyframes are supported.',
            'plan': ['Draw cream background, navy mountain and orange sun; observe and verify.'],
            'requirements': reqs,
            'checkpoints': [{'id': 'visuals', 'description': 'Inspect fixture output',
                             'requirement_ids': [r['id'] for r in reqs]}]})
        return revision

    def finalize(project):
        for req in requirements(project):
            result, _ = call(project, 'observe_requirement', {'requirement_id': req['id']})
            evidence = result[0]
            assert all(Path(path).is_file() and Path(path).is_absolute()
                       for path in evidence['absolute_paths'])
            assert 'data:image' not in json.dumps(result)
            call(project, 'record_review', {'requirement_id': req['id'],
                'evidence_ids': [evidence['id']], 'verdict': 'pass',
                'explanation': 'Scripted integration fixture verdict; not a model quality evaluation.'})
        call(project, 'complete_checkpoint', {'checkpoint_id': 'visuals'})
        export, _ = call(project, 'export_artifact')
        result, _ = call(project, 'finalize_artwork', {'export_id': export['id']})
        assert result['status'] == 'completed'
        return export

    for video in (False, True):
        project = root / ('video' if video else 'poster')
        brief = {'prompt': 'Cream background, navy mountain and orange sun' +
                 (' moving right.' if video else '.'),
                 'spec': {'format': 'mp4' if video else 'png', 'width': 320, 'height': 240,
                          'duration': 1, 'fps': 6, 'seed': 42},
                 'allowed_backends': ['scene2d'],
                 'requirements': [{'id': 'composition', 'description': 'Cream, navy and orange shapes.',
                                   'kind': 'visual'}]}
        if video:
            brief['requirements'].append({'id': 'motion', 'description': 'Sun moves right.',
                'kind': 'temporal', 'observation': {'start': 0, 'end': 0.8, 'samples': 3}})
        invoke('init', project, '--spec-file', write(brief))
        invoke('schemas', project, '--tool', 'put_object')
        call(project, 'describe_environment')
        revision = plan(project)
        # A stale edit must be refused without advancing the revision.
        _, unchanged = call(project, 'put_object', {'expected_revision': revision - 1,
            'object_id': 'invalid', 'source': 'function(ctx){}'}, expected=1)
        assert unchanged == revision
        objects = [
            {'object_id': 'background', 'source': "function(ctx){ctx.fillStyle='#fff4de';ctx.fillRect(0,0,320,240)}", 'layer': 0},
            {'object_id': 'mountain', 'source': "function(ctx){ctx.fillStyle='#16334b';ctx.beginPath();ctx.moveTo(30,210);ctx.lineTo(145,95);ctx.lineTo(260,210);ctx.closePath();ctx.fill()}", 'layer': 1},
            {'object_id': 'sun', 'source': "function(ctx){ctx.fillStyle='#ff8b30';ctx.beginPath();ctx.arc(0,0,22,0,Math.PI*2);ctx.fill()}", 'transform': {'x': 220, 'y': 62}, 'layer': 2}]
        for obj in objects:
            _, revision = call(project, 'put_object', {'expected_revision': revision, **obj})
        if video:
            _, revision = call(project, 'animate_object', {'expected_revision': revision,
                'object_id': 'sun', 'tracks': [{'property': 'x', 'keyframes':
                [{'time': 0, 'value': 180}, {'time': 1, 'value': 260}]}], 'reason': 'Fixture rightward motion'})
        early, _ = call(project, 'export_artifact')
        result, _ = call(project, 'finalize_artwork', {'export_id': early['id']}, expected=1)
        assert result['status'] == 'needs_revision'
        export = finalize(project)
        checks.append(('video' if video else 'poster') + ': export and finalization')
        if not video:
            poster_export = export
            source_project = project
            source_revision = revision
            # Edits invalidate a formerly completed review and checkpoint.
            _, revision = call(project, 'edit_object', {'expected_revision': revision,
                'object_id': 'sun', 'transform': {'x': 230}, 'reason': 'Fixture edit after finalization'})
            report = invoke('verify', project)['result']
            assert not report['eligible_to_finalize']
            checks.append('current revision: old approval invalidated')
    instruction = root / 'edit.txt'
    instruction.write_text('Move the sun 20 pixels right; keep the background and mountain unchanged.')
    target = root / 'edited-poster'
    original_bytes = (source_project / 'versions' / f'{source_revision:06d}.json').read_bytes()
    invoke('versions', source_project)
    invoke('edit', source_project, target, '--revision', source_revision, '--instruction-file', instruction)
    assert (source_project / 'versions' / f'{source_revision:06d}.json').read_bytes() == original_bytes
    edit_state = invoke('state', target)['result']
    assert edit_state['revision'] == 0 and len(edit_state['requirements']) == 2
    revision = plan(target)
    call(target, 'edit_object', {'expected_revision': revision, 'object_id': 'sun',
                              'transform': {'x': 240}, 'reason': instruction.read_text()})
    edited = finalize(target)
    # Use runtime Python for image/video decoding checks.
    decode = root / 'decode.py'
    decode.write_text('''import sys\nfrom PIL import Image, ImageChops\nimport av\na=Image.open(sys.argv[1]).convert("RGB"); b=Image.open(sys.argv[2]).convert("RGB")\nassert a.size == b.size == (320,240)\nassert a.getpixel((5,5)) == (255,244,222)\nassert a.getpixel((220,62)) == (255,139,48)\nassert ImageChops.difference(a.crop((0,90,320,240)), b.crop((0,90,320,240))).getbbox() is None\nassert ImageChops.difference(a,b).getbbox() is not None\nwith av.open(sys.argv[3]) as c:\n frames=list(c.decode(video=0))\n assert len(frames)==6 and frames[0].width==320 and frames[0].height==240\n assert ImageChops.difference(frames[0].to_image(),frames[-1].to_image()).getbbox() is not None\n''')
    subprocess.run([args.python, str(decode), poster_export['absolute_paths'][0],
                    edited['absolute_paths'][0], export['absolute_paths'][0]], check=True)
    checks.append('isolated edit: source snapshot and lower composition preserved')
    checks.append('decoded PNG pixels and six-frame MP4 motion')
    usage = json.loads((target / 'usage.json').read_text())
    assert usage['model_calls'] == 0 and usage['asset_api_calls'] == 0 and usage['tool_calls'] > 0
    checks.append('no model/API calls; persisted tool usage')
    report = {'checks': checks, 'fixture_only': True, 'projects': str(root),
              'poster': poster_export['absolute_paths'][0], 'edit': edited['absolute_paths'][0],
              'video': export['absolute_paths'][0]}
    (root / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
