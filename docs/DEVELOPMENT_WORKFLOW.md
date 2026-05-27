# Development Workflow

## Purpose
This workflow is intended to keep Claude Code focused, reduce chat clutter, and prevent uncontrolled changes.

## Preferred Process
Use this process for development sessions:

1. Open the project folder.
2. Make sure the current code is saved or committed.
3. Ask Claude Code to read `CLAUDE.md` and the relevant docs.
4. Ask Claude Code to inspect the current code before editing.
5. Ask for a short plan for broad or risky work.
6. Approve one focused milestone.
7. Let Claude Code make only the approved change.
8. Run relevant error checks or hooks.
9. Review the changed files.
10. Test manually if needed.
11. Continue to the next milestone.

## Stop Gap Checkpoints
A stop gap checkpoint is a controlled pause after a meaningful step.

At each stop gap, Claude Code should report:
- What was changed
- What files were changed
- What checks were run
- What errors appeared
- What remains to be done
- What decision is needed next

## Small Milestone Examples
Good milestone examples:
- Create GUI shell only
- Add file picker only
- Add output folder selector only
- Add settings file handler only
- Add logging folder creation only
- Add confidence report draft only
- Add installer prompt for shortcuts only
- Replace one OCR engine with updated dependencies
- Add one new output format with engine and settings
- Reorganize settings UI into collapsible sections

Bad milestone examples:
- Build the entire GUI and installer and converter at once
- Refactor everything
- Replace all conversion engines in one step
- Rewrite the whole application
- Add new format, new engine, new UI, and new dependencies all at once

## Dependency Changes
Claude Code should not add dependencies without approval.

When proposing a dependency, Claude should explain:
- What the dependency does
- Why it is needed
- Whether it supports local processing
- Any installation impact
- Any license or maintenance concern if known

## Error Checks and Hooks
After creating or modifying a component, Claude Code should run the relevant check available for the project.

Examples:
- Python syntax check
- Import check
- Unit tests if available
- Lint check if configured
- App launch smoke test
- Installer dry run if safe
- Configured project hooks if they exist later

## Change Summary
After each development task, Claude Code should summarize:
- Files changed
- Purpose of each change
- Errors found
- Tests or checks completed
- How the user can test manually

## Human Control Rule
Claude Code should not make broad architecture changes, delete files, or add major dependencies without user approval.
