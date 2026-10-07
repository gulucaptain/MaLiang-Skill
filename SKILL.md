---
name: maliang
description: Create and revise editable images and procedural animations with MaLiang-Harness, using executable visual programs, rendered feedback, and revision-aware verification. Use for MaLiang requests or visual artwork requiring programmatic control and continued editing; ordinary app development is outside this workflow.
---

# MaLiang

Use the host agent's reasoning and vision to operate MaLiang's existing runtime. Deliver a rendered PNG or MP4 together with its editable project and an accurate verification status. This skill does not start a second LLM or require an LLM API key. Version 1 supports code-created visuals and local asset import; neural asset generation is disabled.

## Runtime entry

Read [the bridge reference](references/bridge.md) for setup, invocation, and argument-file conventions. Run `scripts/harness.py doctor` before the first task in an environment. The runtime is an external dependency; this folder does not bundle MaLiang. Select its root and Python interpreter explicitly when the local defaults do not apply. Do not install dependencies or register the skill globally merely because the skill was invoked.

Initialize a fresh project using an Artwork JSON brief with the user's prompt, requested output specifications, allowed backends, and concrete mandatory requirements. Use `schemas` to discover current capability schemas and backend contracts; read only those relevant to the selected representation. Prefer `scene2d` for independent object editing and keyframes, `svg` for static vector composition, or `canvas` for custom drawing. Use other backends only when actually available and useful.

## Creation loop

- Call `describe_environment`, then `plan_creation`. Cover every mandatory requirement with a checkpoint; retain existing requirement definitions when continuing a project.
- Edit using registered tools and the current authoritative `expected_revision`. Use JSON argument files for code and text. Bound object control is automatic only in `scene2d`; canvas/SVG metadata alone does not move drawn content.
- Render observations for concrete requirements. Open the returned `absolute_paths` with the host's image-viewing tool. A file path or successful render is not visual inspection. If the host cannot see images, stop short of passing visual reviews and report a draft.
- After inspecting evidence, call `record_review` with its evidence IDs, a pass/fail/uncertain verdict, and a concrete explanation. Batch edits around a meaningful goal, then reassess the resulting revision. Temporal requirements need ordered samples across the requested interval; samples do not establish continuity between frames.
- Finish changes before completing checkpoints. Call `export_artifact`, inspect the export as appropriate, and call `finalize_artwork` with the returned export ID. Claim completion only on a successful `completed` result. Exporting a file alone is insufficient.

Keep the persisted tool/frame/runtime budgets. Host model calls, tokens, and time between bridge invocations are outside this meter; apply the host's own limits and avoid unbounded retries. Do not raise budgets silently to evade a stopped run. If quality stalls, compare observed versions, make a targeted correction, or retain a useful draft with `finish_draft` and the unmet requirements. A rejected call requires corrected arguments or a changed state before retrying.

## Continuing and editing

Read current state before changing an existing project. Every commit, including restoration, invalidates earlier reviews and checkpoint approvals. Old images remain useful for comparison, but delivery needs reviews for the delivered revision. Keep updates sequential within a project.

For a separately requested edit, use the bridge `edit` command to create an isolated target project linked to a source revision and the new instruction. Read [editing guidance](references/editing.md) only for this mode. Do not recreate an artwork from a flattened export if its source project is available.

## Delivery

Show the final image/video using an absolute path, and link the editable project state. State whether the result is completed, draft, or budget-limited, mentioning unmet requirements when present. Attribute visual verdicts to the host model's self-assessment; passing harness checks does not establish independent artistic quality. Preserve the user's requested format and style without imposing a preliminary design-selection stage.
