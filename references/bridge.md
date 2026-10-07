# File-based bridge

The host needs shell execution, image viewing, MaLiang source, and its installed Python dependencies. Local default source: `/Users/zhaohaoyu/Documents/05_Code/Davinci`. Override with `--harness /absolute/source` or `MALIANG_HARNESS_ROOT`. Interpreter: `--python /absolute/python`, `MALIANG_PYTHON`, the source's `.venv/bin/python`, a sibling runtime at `Skill/.venv/bin/python`, or the launching Python, in that order. Global options precede the subcommand. Python 3.11+ is required by the Harness.

When dependency installation is requested, use an isolated environment and the source's `pyproject.toml`; install Chromium via that environment's `python -m playwright install chromium`. Alternatively set `DAVINCI_CHROMIUM` to an existing compatible browser executable. When Playwright Chromium is absent on this Mac, the bridge can use the installed Google Chrome executable. `doctor` checks imports and browser existence, not a successful render. This bridge never loads `.env`, starts the internal agent, or calls a model provider. It disables plugin discovery and neural generation. Imported local assets still use registered tools.

Use the actual skill directory in place of `SKILL_ROOT`, and absolute paths for task files and projects:

```sh
python3 SKILL_ROOT/scripts/harness.py --harness /absolute/Davinci --python /absolute/venv/bin/python doctor
python3 SKILL_ROOT/scripts/harness.py --python /absolute/venv/bin/python init /absolute/project --spec-file /absolute/brief.json
python3 SKILL_ROOT/scripts/harness.py --python /absolute/venv/bin/python schemas /absolute/project --tool plan_creation
python3 SKILL_ROOT/scripts/harness.py --python /absolute/venv/bin/python call /absolute/project plan_creation --args-file /absolute/plan.json
python3 SKILL_ROOT/scripts/harness.py --python /absolute/venv/bin/python state /absolute/project
python3 SKILL_ROOT/scripts/harness.py --python /absolute/venv/bin/python verify /absolute/project
```

Create argument files with file-writing tools, not interpolated shell text. Tool schemas are obtained live rather than copied into this skill. Calls return `current_revision` plus the tool result. Evidence text is decoded into JSON, image payloads are omitted, and evidence `paths` receive corresponding `absolute_paths`. Read those files using the host image viewer. Errors and refused finalization exit nonzero; inspect their JSON before correcting the next call. `verify` reports eligibility without changing the delivery status.

Minimal image brief:

```json
{
  "prompt": "A cream poster with an orange sun and navy mountain, with ample empty space.",
  "spec": {"format": "png", "width": 640, "height": 480, "duration": 1, "fps": 12, "seed": 42},
  "allowed_backends": ["scene2d", "canvas", "svg"],
  "requirements": [
    {"id": "composition", "kind": "visual", "description": "An orange sun and navy mountain are visible on cream with ample empty space.", "hard": true}
  ]
}
```

List source revisions and create an isolated editing task:

```sh
python3 SKILL_ROOT/scripts/harness.py --python /absolute/venv/bin/python versions /absolute/source-project
python3 SKILL_ROOT/scripts/harness.py --python /absolute/venv/bin/python edit /absolute/source-project /absolute/new-edit --revision 3 --instruction-file /absolute/edit.txt
```

Initialization enforces `guided` workflow and code-only policy. It rejects occupied projects and prepopulated executable content. Supply `--budget-file` to persist custom `Budget` settings; otherwise the Harness defaults apply. For MP4 choose even dimensions, a duration and FPS within the runtime limits, and an animation-capable backend. A temporal requirement's observation can specify `start`, `end`, and `samples` (at least three distinct times). Keep endpoint samples within the visible interval when objects have an exclusive end time.

Budget tool/frame counters and execution seconds persist in `usage.json` across bridge calls. Locking serializes bridge commands for each project. External callers must also avoid simultaneous changes. Host thinking time and model usage are not counted. Runtime-generated files, snapshots, traces and exports live in the chosen project, outside the skill folder.

## Offline integration check

Run `scripts/smoke_test.py --harness SOURCE --python RUNTIME_PYTHON` with the selected runtime. It creates temporary projects, renders a PNG and MP4, tests stale revisions and completion gates, and verifies an isolated edit with pixel comparisons. Reviews are scripted fixtures, not evaluations of LLM creation quality. Its JSON report identifies the retained temporary artifacts. Chromium may need process permissions beyond a restricted shell sandbox.
