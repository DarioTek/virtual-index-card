# AGENTS.md
# Plan-Driven AI Agent Operating Instructions

## 1. Mission

Act as a disciplined software development agent. Analyze, plan, implement, test, and document work in small, verifiable steps.

**Do not begin substantial implementation before creating or updating `PLAN.md`.**

Follow the repository's existing conventions and any higher-priority instructions. Preserve user changes and never claim an action or test succeeded unless it actually did.

## 2. Standard Project Structure

Use the following structure as the default for a new project. Adapt it to the project's language, framework, and scale; do not create empty folders or move existing files without a reason.

```text
my-project/
├── AGENTS.md
├── PLAN.md
├── BACKLOG.md
├── README.md
├── docs/
│   ├── architecture.md
│   ├── technical-decisions.md
│   └── backlog-archive.md
├── src/
├── tests/
└── ... (configuration, scripts, deployment, and other project-specific files)
```

### Directory and file responsibilities

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Persistent operating instructions for AI agents |
| `PLAN.md` | Current assignment, task sequence, and execution progress |
| `BACKLOG.md` | Active and future work not currently being executed |
| `README.md` | Project overview, setup, usage, and developer instructions |
| `docs/architecture.md` | Current system architecture and important structural diagrams |
| `docs/technical-decisions.md` | Architecture and implementation decisions with rationale |
| `docs/backlog-archive.md` | Completed backlog items retained for historical traceability |
| `src/` | Application or library source code |
| `tests/` | Automated tests, organized consistently with the source where practical |

Use `docs/` (plural) as the documentation directory. Do not create a separate `doc/` directory unless an existing project convention or tool requires it.

## 3. Project Control Files

Maintain these files in the repository root:

### AGENTS.md — Operating Instructions
- Read this file before starting work.
- Treat it as the persistent operating guide.
- Do not change it unless the user asks or approves a necessary change.

### PLAN.md — Active Execution Plan
- Keep it focused on the active assignment.
- Record the objective, scope, approach, tasks, acceptance criteria, risks, test strategy, decisions, and progress.
- Update it throughout execution, not only at the end.
- Do not mark work complete until its acceptance criteria have been verified.

### BACKLOG.md — Active Project Backlog
- Maintain the inventory of proposed, ready, in-progress, blocked, and deferred work.
- Capture future features, bugs, technical debt, performance/security improvements, infrastructure work, documentation, and useful ideas.
- Give each item a stable unique ID such as `BL-001`.
- Record description, category, priority, status, acceptance criteria, dependencies, and date added.
- Check for duplicates before adding an item.
- Do not implement backlog items merely because they are listed. Implement them when the user selects or authorizes them.
- Move completed items to `docs/backlog-archive.md` after recording their completion details. Never reuse their IDs.

### docs/backlog-archive.md — Completed Backlog History
- Store completed backlog items, preserving their original IDs and relevant details.
- Include completion date and a validation, plan, commit, pull request, or release reference when available.
- Do not delete or recycle archived IDs.
- Keep active work in `BACKLOG.md`; the archive is historical and is not an authorization to reopen work.

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

1. Read `AGENTS.md`, `PLAN.md` (if present), `BACKLOG.md`, and relevant files in `docs/`.
2. Inspect the repository structure and relevant documentation.
3. Inspect Git status, current branch, and existing changes. Do not overwrite or discard user work.
4. Review relevant source code, tests, configuration, and dependencies.
5. Restate the objective, expected outcomes, scope, assumptions, and constraints.
6. Identify affected components, dependencies, risks, and unknowns.
7. Create or update `PLAN.md` with an actionable, ordered task breakdown.
8. Define acceptance criteria and a proportionate validation strategy.
9. Identify relevant backlog items and reference their IDs in the plan.

For substantial, risky, or architectural changes, present the plan and wait for approval unless the user has already authorized execution. For routine, low-risk work, proceed within the user's request without unnecessary interruptions. Ask a concise clarification when essential information is missing.

## 5. Planning Requirements

A useful plan must:
- Break work into small logical tasks.
- Put tasks in dependency order.
- Identify files or components likely to change when known.
- Define observable acceptance criteria.
- Include tests and validation.
- Identify risks and rollback considerations for risky changes.
- Distinguish confirmed facts from assumptions.

Do not invent repository details. Mark unknowns as items to investigate.

## 6. Execution Procedure

For each logical task:

1. Mark it `In Progress` in `PLAN.md` before starting.
2. Inspect the relevant implementation before editing.
3. Make a focused change consistent with project conventions.
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

## 8. Backlog Management and Archiving

Add an item to `BACKLOG.md` when work is useful but outside the active assignment, including follow-up enhancements, separate defects, technical debt, missing automation, observability, documentation, or test coverage.

Before adding an item:
1. Search the active backlog and archive for duplicates.
2. Assign the next available stable ID.
3. Write an actionable description and observable acceptance criteria.
4. Set category, priority, status, and date added.
5. Record dependencies and context where useful.

When a backlog item is selected:
1. Reference its ID in `PLAN.md`.
2. Change its status in `BACKLOG.md` to `In Progress`.
3. Implement and validate it through the normal workflow.
4. On verified completion, move the full item to `docs/backlog-archive.md`.
5. Record its completion date and validation/delivery reference in the archive.
6. Remove it from the active section of `BACKLOG.md` and update the summary counts.

Do not archive an item merely because code was written. Archive only after the acceptance criteria have been verified. If an item is reopened, move it back to `BACKLOG.md` with the same ID and record the reopening context; never create a duplicate ID.

## 9. Errors, Blockers, and Plan Changes

When something fails:
1. Capture the exact failure and relevant context.
2. Investigate the root cause before changing unrelated code.
3. Make a reasonable fix if it is within scope and authorized.
4. Re-run relevant validation.
5. Document the outcome.

If unresolved, mark the task `Blocked`, explain why, and state what is needed to unblock it. Add a backlog item when the issue is separate from the active assignment.

If the approach must change, update `PLAN.md` with the reason, impact, revised tasks, and any approval needed. Preserve completed work and meaningful history.

## 10. Testing and Quality

Choose validation appropriate to the change. This may include unit, integration, regression, API, end-to-end, security, lint, formatting, type-check, or build checks.

- Run tests that are relevant and available.
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
- Never expose, commit, or copy secrets, credentials, tokens, or private environment files.
- Ask before destructive, externally visible, costly, or security-sensitive actions.
- Follow least-privilege principles.

## 12. Session Recovery

At the beginning of every resumed session:

1. Read the three control files and relevant documentation.
2. Inspect Git status and the actual repository state.
3. Compare recorded progress with the code and test results.
4. Re-verify tasks marked `In Progress` or recently `Completed` when appropriate.
5. Resume from the next valid task; do not repeat verified completed work unnecessarily.
6. Correct stale or inaccurate documentation before proceeding.

The files are records, not proof. Verify the real project state.

## 13. Completion Checklist

Before reporting an assignment complete:

- [ ] All in-scope tasks are completed or explicitly identified as blocked/deferred.
- [ ] Acceptance criteria have been checked.
- [ ] Relevant tests and validation have been run.
- [ ] Failures and unrun checks are disclosed.
- [ ] The final diff has been reviewed.
- [ ] `PLAN.md` reflects the verified final state.
- [ ] `BACKLOG.md` includes relevant new work and updated selected items.
- [ ] Completed backlog items have been moved to `docs/backlog-archive.md`.
- [ ] Remaining limitations and follow-up work are documented.

## 14. Final Response

Provide a concise report with:
- Summary of the change.
- Files created, modified, or deleted.
- Tests/checks run and their actual results.
- Backlog items added, updated, completed, or archived.
- Outstanding issues, assumptions, and limitations.
- Recommended next step.

## Golden Rule

**Plan before substantial changes, update progress continuously, validate before claiming completion, and preserve enough context for another agent session to continue safely.**
