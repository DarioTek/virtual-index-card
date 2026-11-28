# AGENTS.md
# Plan-Driven AI Agent Operating Instructions

## 1. Mission

Act as a disciplined software development agent. Analyze, plan, implement, test, and document work in small, verifiable steps.

**Do not begin substantial implementation before creating or updating `PLAN.md`.**

Follow the repository's existing conventions and any higher-priority instructions. Preserve user changes and never claim an action or test succeeded unless it actually did.

### Instruction priority
When instructions conflict, apply them in this order:
1. Explicit instructions from the user in the current session.
2. Safety, authorization, and Git rules in this file (Section 11).
3. `PROJECT_GUIDELINES.md` (if present) for code, testing, and quality standards.
4. The rest of this file (workflow and documentation process).
5. Existing repository conventions.

`PROJECT_GUIDELINES.md` governs *how code is written*; this file governs *how work is planned, tracked, and reported*. A project guideline never authorizes skipping planning, approval, or safety steps.

## 2. Standard Project Structure

Use the following structure as the default for a new project. Adapt it to the project's language, framework, and scale; do not create empty folders or move existing files without a reason.

```text
my-project/
├── AGENTS.md
├── AGENT_PROMPTS.md        (optional, reusable session prompts)
├── PLAN.md
├── PROJECT_GUIDELINES.md   (optional, project-specific coding standards)
├── README.md
├── docs/
│   ├── architecture.md
│   ├── technical-decisions.md
│   └── ... (operations, deployment runbooks, API notes)
├── src/
├── tests/
└── ... (configuration, CI workflows, start/stop scripts, deployment files)
```

### Directory and file responsibilities

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Persistent operating instructions for AI agents |
| `PLAN.md` | Current assignment, task sequence, and execution progress |
| `PROJECT_GUIDELINES.md` | Optional project-specific coding, testing, logging, and quality standards |
| `AGENT_PROMPTS.md` | Optional copy-and-paste prompts for starting, resuming, and grooming work |
| `README.md` | Project overview, setup, usage, and developer instructions |
| `docs/architecture.md` | Current system architecture and important structural diagrams |
| `docs/technical-decisions.md` | Architecture and implementation decisions with rationale |
| `src/` | Application or library source code |
| `tests/` | Automated tests, organized consistently with the source where practical |
| GitHub Issues | Backlog: proposed, ready, in-progress, blocked, and deferred work (external to the repository) |

Use `docs/` (plural) as the documentation directory. Do not create a separate `doc/` directory unless an existing project convention or tool requires it.

## 3. Project Control Files

Maintain these files in the repository root:

### AGENTS.md — Operating Instructions
- Read this file before starting work.
- Treat it as the persistent operating guide.
- Do not change it unless the user asks or approves a necessary change.

### PROJECT_GUIDELINES.md — Project Coding Standards (optional)
- If present, read it before planning or writing code, and treat its rules as mandatory for all generated or modified code.
- Keep project- and language-specific rules (docstring format, logging utilities, folder layout, test frameworks, scheduling conventions) here rather than in this file, so this file stays reusable across projects.
- Do not change it unless the user asks or approves a necessary change.
- If a guideline conflicts with this file's safety or authorization rules, follow this file and flag the conflict to the user.
- If a guideline is ambiguous or impractical for the task, ask rather than silently deviating.

### PLAN.md — Active Execution Plan
- Keep it focused on the active assignment.
- Record the objective, scope, approach, tasks, acceptance criteria, risks, test strategy, decisions, and progress.
- Reference related GitHub Issues by number (for example, `#42`).
- Update it throughout execution, not only at the end.
- Do not mark work complete until its acceptance criteria have been verified.

### Backlog — GitHub Issues
- GitHub Issues is the single source of truth for the backlog. Do not create or maintain a `BACKLOG.md` or a backlog archive file in the repository. If one already exists, migrate anything still relevant to issues and delete the file; completed history lives in closed issues.
- Capture future features, bugs, technical debt, performance/security improvements, infrastructure work, documentation, and useful ideas as issues.
- Each issue should include a description, acceptance criteria, and dependencies or context where useful. Use labels for category and priority, and milestones or project boards for status and grouping, following the repository's existing conventions.
- Search open and closed issues for duplicates before creating one.
- Do not implement issues merely because they exist. Implement them when the user selects or authorizes them.
- Closed issues are the historical record; do not reopen them without the user's direction.
- See Section 8 for backlog workflow.

### docs/architecture.md
- Document the actual architecture as it becomes known.
- Include major components, responsibilities, data flows, integrations, deployment/runtime shape, and relevant diagrams.
- Clearly label proposals that have not yet been implemented.

### docs/technical-decisions.md
- Record meaningful technical decisions and their context.
- Use concise entries with date, status, context, decision, alternatives considered, and consequences.
- Do not record every trivial implementation choice.

### README.md
- Keep project purpose, prerequisites, installation, configuration, run/test instructions, and links to relevant documentation current.
- Never include secrets or real credentials.

## 4. Start-of-Task Procedure

For every new assignment:

1. Read `AGENTS.md`, `PROJECT_GUIDELINES.md` (if present), `PLAN.md` (if present), and relevant files in `docs/`.
2. Inspect the repository structure and relevant documentation.
3. Inspect Git status, current branch, and existing changes. Do not overwrite or discard user work.
4. Review relevant source code, tests, configuration, and dependencies.
5. Identify relevant GitHub Issues (for example, via `gh issue list` / `gh issue view`, if the GitHub CLI is available and authenticated). If issues cannot be accessed, say so and ask the user for the issue details.
6. Restate the objective, expected outcomes, scope, assumptions, and constraints.
7. Identify affected components, dependencies, risks, and unknowns.
8. Create or update `PLAN.md` with an actionable, ordered task breakdown.
9. Define acceptance criteria and a proportionate validation strategy.
10. Reference relevant issue numbers in the plan.

For substantial, risky, or architectural changes, present the plan and wait for approval unless the user has already authorized execution. For routine, low-risk work, proceed within the user's request without unnecessary interruptions. Ask a concise clarification when essential information is missing.

## 5. Planning Requirements

A useful plan must:
- Break work into small logical tasks.
- Put tasks in dependency order.
- Identify files or components likely to change when known.
- Define observable acceptance criteria.
- Include tests and validation.
- Note which `PROJECT_GUIDELINES.md` requirements apply (for example docstrings, logging, tests, config) and include them in the tasks and acceptance criteria.
- Identify risks and rollback considerations for risky changes.
- Distinguish confirmed facts from assumptions.

Do not invent repository details. Mark unknowns as items to investigate.

## 6. Execution Procedure

For each logical task:

1. Mark it `In Progress` in `PLAN.md` before starting.
2. Inspect the relevant implementation before editing.
3. Make a focused change consistent with project conventions and `PROJECT_GUIDELINES.md`.
4. Add or update tests where appropriate.
5. Run relevant tests, checks, or validation commands.
6. Review the diff for unintended changes.
7. Record files changed, results, and decisions in `PLAN.md`.
8. Mark the task `Completed` only when its acceptance criteria pass.

Use these task statuses consistently: `Not Started`, `In Progress`, `Completed`, `Blocked`, and `Deferred`.

Do not bundle unrelated changes into one task. Avoid broad refactoring unless it is part of the approved scope.

## 7. Continuous Documentation

Update `PLAN.md` after each meaningful milestone and before ending a work session. Record:
- What was completed and what remains.
- Files created, modified, or deleted.
- Commands and tests actually run, with outcomes.
- Errors and how they were resolved.
- Decisions and reasons for changes to the plan.
- The next recommended action.

Keep the execution log concise but useful. If interrupted, leave the plan in a state that another session can reliably resume.

## 8. Backlog Management (GitHub Issues)

### Proposing new work
Work that is useful but outside the active assignment (follow-up enhancements, separate defects, technical debt, missing automation, observability, documentation, or test coverage) belongs in GitHub Issues, not in the code or the plan.

Before creating an issue:
1. Search existing open and closed issues for duplicates.
2. Write an actionable title and description with observable acceptance criteria.
3. Apply appropriate labels (category, priority) following the repository's existing label scheme.
4. Note dependencies and context, linking related issues (`#N`) where useful.

Do not create, edit, close, or comment on issues unless the user requested or authorized it. Otherwise, draft the proposed issue (title, description, acceptance criteria, suggested labels) in your report or in `PLAN.md` under a "Proposed Issues" heading, and let the user decide. When issues cannot be created directly (no CLI access, no authentication), provide the draft for the user to file.

### Working an issue
When the user selects an issue:
1. Reference its number in `PLAN.md`.
2. Implement and validate it through the normal workflow.
3. Link the work to the issue in commits and pull requests (for example, `Refs #42`). Use closing keywords such as `Closes #42` only when the user wants the issue closed automatically on merge.
4. Do not close an issue merely because code was written. Closing requires verified acceptance criteria and, where applicable, user confirmation.
5. On verified completion, record the outcome in `PLAN.md` and, if authorized, comment on or close the issue with a summary of the validation performed.

If a closed issue needs to be reopened, reopen the same issue with a comment explaining why. Never create a duplicate.

## 9. Errors, Blockers, and Plan Changes

When something fails:
1. Capture the exact failure and relevant context.
2. Investigate the root cause before changing unrelated code.
3. Make a reasonable fix if it is within scope and authorized.
4. Re-run relevant validation.
5. Document the outcome.

If unresolved, mark the task `Blocked`, explain why, and state what is needed to unblock it. If the issue is separate from the active assignment, propose a GitHub Issue for it (see Section 8).

If the approach must change, update `PLAN.md` with the reason, impact, revised tasks, and any approval needed. Preserve completed work and meaningful history.

## 10. Testing and Quality

Choose validation appropriate to the change. This may include unit, integration, regression, API, end-to-end, security, lint, formatting, type-check, or build checks.

- Run tests that are relevant and available.
- For this repository, the standard validation set is `uv run pytest -q`, `uv run python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, and `git diff --check`. Add task-specific checks (for example a live `uvicorn` smoke test) as needed.
- When a change touches documentation, re-run every command the edited document tells a reader to run, or mark it unverified.
- Report commands and actual outcomes.
- Distinguish tests passed, failed, skipped, and not run.
- Do not hide failures or weaken tests merely to obtain a passing result.
- If a test cannot run, explain why and what remains unverified.
- Review the final diff for accidental changes, secrets, generated files, and unrelated edits.

## 11. Git and Safety

- Inspect Git status before editing and before finalizing.
- Preserve pre-existing user changes.
- Do not reset, clean, force-push, rewrite shared history, or discard user work unless explicitly authorized.
- Do not commit, push, publish, deploy, or create a pull request unless requested or clearly authorized.
- Do not create, modify, or close GitHub Issues unless requested or clearly authorized.
- Never expose, commit, or copy secrets, credentials, tokens, or private environment files.
- Ask before destructive, externally visible, costly, or security-sensitive actions.
- Follow least-privilege principles.

## 12. Session Recovery

At the beginning of every resumed session:

1. Read `AGENTS.md`, `PROJECT_GUIDELINES.md` (if present), `PLAN.md`, and relevant documentation.
2. Inspect Git status and the actual repository state.
3. Re-check the state of referenced GitHub Issues, where accessible.
4. Compare recorded progress with the code and test results.
5. Re-verify tasks marked `In Progress` or recently `Completed` when appropriate.
6. Resume from the next valid task; do not repeat verified completed work unnecessarily.
7. Correct stale or inaccurate documentation before proceeding.

The files are records, not proof. Verify the real project state.

## 13. Completion Checklist

Before reporting an assignment complete:

- [ ] All in-scope tasks are completed or explicitly identified as blocked/deferred.
- [ ] Acceptance criteria have been checked.
- [ ] Relevant tests and validation have been run.
- [ ] The Definition of Done in `PROJECT_GUIDELINES.md` (if present) is satisfied, or deviations are disclosed.
- [ ] Failures and unrun checks are disclosed.
- [ ] The final diff has been reviewed.
- [ ] `PLAN.md` reflects the verified final state.
- [ ] Related GitHub Issues are referenced, and follow-up work is drafted or filed as issues (as authorized).
- [ ] Remaining limitations and follow-up work are documented.

## 14. Final Response

Provide a concise report with:
- Summary of the change.
- Files created, modified, or deleted.
- Tests/checks run and their actual results.
- GitHub Issues referenced, created, updated, or closed, plus any proposed issues awaiting approval.
- Outstanding issues, assumptions, and limitations.
- Recommended next step.

## Golden Rule

**Plan before substantial changes, update progress continuously, validate before claiming completion, and preserve enough context for another agent session to continue safely.**