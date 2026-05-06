# Claude Code Prompt Templates

Use these prompts inside Claude Code to keep sessions short and controlled.

## First Project Inspection
```text
Read CLAUDE.md and the docs folder. Inspect the current project. Do not edit files yet. Summarize what the tool currently does and recommend the next safest milestone.
```

## Ask for a Plan Only
```text
Read CLAUDE.md and the relevant docs. Inspect the code related to this request. Do not edit files yet. Propose a short plan with milestones and stop gap checkpoints.
```

## One Focused Change
```text
Implement only the approved milestone. Change only files directly related to this task. Run relevant error checks or configured hooks after the change. Summarize changed files, errors, and testing steps.
```

## GUI Work
```text
Read docs/GUI_REQUIREMENTS.md and CLAUDE.md. Inspect the current app structure. Propose the smallest next GUI milestone. Do not edit until the plan is approved.
```

## Conversion Engine Work
```text
Read docs/CONVERSION_REQUIREMENTS.md and docs/LOCAL_PROCESSING_RULES.md. Inspect the current conversion code. Recommend the best local conversion approach for the next milestone. Do not add dependencies without approval.
```

## Installer Work
```text
Read docs/INSTALLER_UNINSTALLER_REQUIREMENTS.md and CLAUDE.md. Inspect current launcher or installer files. Propose a safe installer milestone. Do not edit files until approved.
```

## Logging Work
```text
Read docs/LOGGING_REQUIREMENTS.md. Inspect the current logging or error handling approach. Propose one small logging improvement. Do not edit until approved.
```

## Confidence Reporting Work
```text
Read docs/CONFIDENCE_REPORTING.md and docs/CONVERSION_REQUIREMENTS.md. Inspect the current output generation process. Propose one small milestone for confidence reporting. Do not edit until approved.
```

## Debugging
```text
Inspect the error and the related files. Do not make broad changes. Identify the likely cause, propose a minimal fix, then wait for approval before editing.
```

## After Claude Makes Changes
```text
Summarize exactly what changed, which files changed, what checks were run, what errors remain, and how I can manually test this step.
```
