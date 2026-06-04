# CLAUDE.md

## Project Name
Markwell

## Project Purpose
This project is a local processing tool that converts documents and document based files into clean, organized Markdown for human review, AI upload, memory systems, and knowledgebase repositories.

The tool should support conversion workflows for PDFs, Word documents, DOCX files, Excel files, CSV files, datasets, tables, matrices, images with text, electrical drawings with text, and embedded images or drawings contained in source documents.

## Core Principle
The tool must prioritize accurate structure preservation. Output Markdown should remain organized and should follow the source document structure as closely as possible, including headings, text order, tables, matrices, image references, drawings, captions, and embedded content placement.

## Local Processing Rule
This tool is local processing only. Do not add cloud processing, external API processing, telemetry, remote file upload, or online conversion services unless the user explicitly approves that change later.

## Development Rules
- Inspect before editing.
- Use short plans for broad or risky tasks.
- Work in small milestones with stop gap checkpoints.
- Change only files related to the approved task.
- Do not delete files or add dependencies without approval.
- Run relevant error checks or configured hooks after component changes.
- Summarize changed files, errors, and testing steps.

## Claude Code Working Behavior
When asked to work on this project, first read this file and the relevant files in the `docs/` folder. Then inspect the current codebase before proposing changes.

For broad or risky work, propose a short plan before editing. Keep changes focused and avoid unrelated refactoring.

Use stop gap checkpoints after meaningful milestones. At each checkpoint, explain what changed, what was verified, what errors were found, and what should happen next.

## Important Reference Files
- `docs/PROJECT_SPEC.md` explains the project vision and scope.
- `docs/FEATURE_REQUIREMENTS.md` lists the required features.
- `docs/GUI_REQUIREMENTS.md` explains the expected interface.
- `docs/CONVERSION_REQUIREMENTS.md` explains conversion behavior and output expectations.
- `docs/LOCAL_PROCESSING_RULES.md` defines local only processing requirements.
- `docs/CONFIDENCE_REPORTING.md` explains confidence scoring and user trust reporting.
- `docs/INSTALLER_UNINSTALLER_REQUIREMENTS.md` defines install and uninstall expectations.
- `docs/LOGGING_REQUIREMENTS.md` explains logging requirements.
- `docs/DEVELOPMENT_WORKFLOW.md` explains the preferred build workflow.
- `docs/CLAUDE_PROMPT_TEMPLATES.md` provides reusable prompts for the user.

## Output Goal
The tool should produce Markdown files that are useful for:
- Human reading
- AI tool upload
- Knowledgebase repositories
- Documentation analysis
- Long term document organization

## User Experience Goal
The tool should feel simple, clean, and reliable. The interface should guide non technical users through selecting files, choosing settings, understanding conversion risks, reviewing confidence results, and locating final Markdown output.
