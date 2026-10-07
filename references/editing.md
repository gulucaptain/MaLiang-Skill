# Isolated edits

Use the bridge `versions` command on the source project. Inspect the requested revision and its full-frame evidence before choosing an edit. Write the user's new instruction to a UTF-8 text file. Run `edit SOURCE TARGET --revision K --instruction-file FILE` (global runtime options precede `edit`). The bridge calls the Harness's `create_edit` function to create a fresh revision sequence, copy editable content and retain source provenance. Use a new destination outside the source project. `--budget-file` optionally sets the target's budget; source usage is not inherited.

Switch subsequent calls to the returned target project. Read state, inspect `inspect_edit_source` when available, plan the edit with the target's existing requirements, and make a targeted program/object change. If an inherited requirement directly conflicts with the new instruction, discover and use `revise_edit_requirement`, quoting that instruction and preserving unaffected clauses. The new edit acceptance requirement cannot be changed. Do not weaken unrelated constraints.

Compare old and new renderings at matching times, including preserved regions when requested. Unchanged pixels in one region do not establish overall semantic consistency. If baseline rendering fails, read `edit.json` for the reason and inspect the source program or available source evidence; do not claim a visual comparison you did not perform.

The target starts without the source's reviews. Re-observe and review its current revision, complete checkpoints, export, and finalize. Restoring a version within a run instead makes a new revision while retaining that run's requirements. Use an isolated edit for a separately requested task with new constraints.
