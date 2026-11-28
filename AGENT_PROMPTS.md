# AI Agent Prompt Library

Copy-and-paste prompts for working with `AGENTS.md` and `PLAN.md`. Backlog work is tracked in GitHub Issues.

| Prompt | When to use |
|---|---|
| [1. Initialize a project](#1-initialize-a-project) | First session in a new or newly adopted repository |
| [2. Start a new assignment](#2-start-a-new-assignment) | Beginning a new feature, fix, or GitHub Issue |
| [3. Resume a session](#3-resume-a-session) | Continuing work after a break or in a fresh agent session |
| [4. Groom GitHub Issues](#4-groom-github-issues) | Reviewing the backlog for requirements, acceptance criteria, and test plans |
| [Optional add-ons](#optional-add-ons) | Authorizing issue creation, approving plans, documenting architecture |
| [Pausing and resuming work](#pausing-and-resuming-work) | Stopping at a specific task or checkpoint and continuing later |

---

## 1. Initialize a project

```markdown
Read AGENTS.md and PLAN.md (if it exists), and follow AGENTS.md as your operating instructions for this session.

I am initializing a new software project.

## Project context (optional; delete if unknown)
- Purpose: <what the project does and for whom>
- Preferred stack: <languages, frameworks, tools>
- Constraints: <deadlines, hosting, compliance, etc.>

## Step 1: Discover
Inspect the repository: structure, languages, frameworks, dependencies, configuration, tests, CI, existing documentation, and Git status/history. Identify conventions already in use. Check whether the GitHub CLI is available and authenticated, and review any existing GitHub Issues. Do not invent details; list anything you cannot determine as an open question.

## Step 2: Propose
- Summarize what you found, separating confirmed facts from assumptions.
- Propose the project architecture (components, responsibilities, data flow, integrations, runtime/deployment shape). Label everything as proposed.
- Propose a tech stack and project structure only where the repository doesn't already define them, with brief rationale and alternatives for any significant choice.
- Recommend an initial development roadmap broken into phases or milestones.

## Step 3: Document (planning artifacts only)
- Create an initial PLAN.md for the first assignment (objective, scope, tasks in dependency order, acceptance criteria, test strategy, risks, open questions).
- Under "Proposed Issues" in PLAN.md, draft the future work you identified (title, description, acceptance criteria, suggested labels). Do not create GitHub Issues yet.
- Note any operations surface the project will need documented (start/stop scripts, CI workflows, deployment runbooks, environment-variable examples) as proposed documents in PLAN.md rather than writing them now.
- Do not create or modify any other files (including docs/architecture.md, README.md, or source code) until I approve.

## Constraints
- Do not begin implementation.
- Do not commit, push, install dependencies, or create/modify GitHub Issues without my approval.
- Preserve any existing user changes.

## Deliverable
Present your findings, proposed architecture, roadmap, and the initial PLAN.md for my review. End with a short list of the decisions or clarifications you need from me before proceeding.
```

---

## 2. Start a new assignment

```markdown
Read AGENTS.md and PLAN.md, and inspect Git status and the current repository state.

New assignment: <describe the goal, or "work on GitHub Issue #N">.

Follow the Start-of-Task Procedure in AGENTS.md. Update PLAN.md with the objective, scope, tasks, acceptance criteria, and validation strategy, then present the plan for my approval before implementing.
```

---

## 3. Resume a session

```markdown
Read AGENTS.md and PLAN.md, then follow the Session Recovery procedure: inspect Git status, check the actual repository state against the recorded progress, and re-verify anything marked In Progress or recently Completed.

Report what is accurate, what is stale, and your recommended next step. Wait for my go-ahead before continuing.
```

---

## 4. Groom GitHub Issues

Reviews open issues and drafts improvements. Nothing in GitHub changes until you approve.

```markdown
Read AGENTS.md and PROJECT_GUIDELINES.md (if present), and follow them as your operating instructions.

Task: review and groom the open GitHub Issues in this repository. Do not implement anything and do not modify the code.

## Step 1: Gather
- Use the GitHub CLI (`gh issue list`, `gh issue view`) to read open issues, including their comments, labels, milestones, and linked PRs. Scope: <all open issues | issues labeled X | issues #N-#M>.
- Read README.md, docs/architecture.md, and docs/technical-decisions.md (if present) so your review reflects how the system actually works.
- If you cannot access GitHub, tell me and ask me to paste the issues.

## Step 2: Assess each issue against this checklist
- **Title:** clear, specific, action-oriented.
- **Problem / context:** why this matters, who is affected, and the business or technical value.
- **Requirements:** what must be true; separate functional from non-functional (performance, security, reliability, logging, compatibility).
- **Scope:** explicit in-scope and out-of-scope.
- **Acceptance criteria:** specific, observable, and testable (checklist or Given/When/Then); no vague terms like "works well" or "improve."
- **Test and validation plan:** how to verify it (unit, integration, UI/end-to-end, manual steps, sample inputs and expected outputs, edge cases, error paths, regression risk).
- **Dependencies and blockers:** related issues, external systems, required decisions.
- **Technical notes:** affected components or files, risks, assumptions, open questions. Mark assumptions as assumptions; do not invent details.
- **Classification:** type, labels, priority, and a rough size estimate.
- **Hygiene:** duplicates, stale or obsolete items, conflicting requirements, and issues too large to complete in one assignment (suggest how to split them).
- **Definition of Done:** the issue should reference or fit the Definition of Done in PROJECT_GUIDELINES.md, including docs and tests.

## Step 3: Report (no changes to GitHub yet)
Present:
1. A summary table: issue number, title, readiness (Ready / Needs Work / Blocked / Duplicate / Stale), and the top gaps.
2. For each issue that needs work, a proposed rewrite of the title and body, using the template below, with new or changed content clearly marked.
3. Proposed label, priority, and milestone changes.
4. Proposed splits, merges, and closures, with reasons.
5. A recommended order of work based on priority and dependencies.
6. Questions you need me to answer to fill in the gaps. Ask these rather than guessing.

## Issue template to use for rewrites
**Summary / Problem:**
**Requirements:**
**Out of scope:**
**Acceptance criteria:**
- [ ] ...
**Test / validation plan:**
**Dependencies:**
**Technical notes / risks / open questions:**

## Constraints
- Do not create, edit, comment on, label, or close any issue until I approve the specific changes.
- Do not modify repository files, commit, or push.
- Preserve the original intent of each issue; flag anything where you are unsure of that intent instead of changing it.
```

**Apply the approved grooming changes** (after you review the report):

```markdown
Approved: apply the proposed changes for issues #<list> only. Use `gh issue edit` for titles, bodies, and labels. Post a short comment on each noting what was groomed. Do not close anything. Report the final state of each updated issue.
```

**Tips**
- Groom in small batches (5 to 10 issues) by narrowing the scope line to a label or issue range.
- Answer the agent's questions before approving rewrites; acceptance criteria written without your answers are just assumptions.

---

## Optional add-ons

**Authorize the agent to file issues after you approve the drafts** (append to Prompt 1 or 2):

```markdown
After I approve the drafted issues, create them with `gh issue create` using the suggested labels, and report the issue numbers.
```

**Approve the plan and begin implementation:**

```markdown
The plan is approved. Proceed with implementation following AGENTS.md: mark each task In Progress before starting, validate after each task, and keep PLAN.md updated. Do not commit or push until I ask.
```

**Document the approved architecture** (after Prompt 1 review):

```markdown
The architecture is approved. Create docs/architecture.md and docs/technical-decisions.md, and update README.md with project overview and setup instructions. Do not modify source code. Show me the diff when done.
```

---

## Pausing and resuming work

**Stop after a specific task** (from the start of the session):

```markdown
Read AGENTS.md and PLAN.md, then continue with the next task.

Execute tasks 1 through 3 only. Stop after Task 3 is completed and validated; do not start Task 4.

Before stopping:
- Update PLAN.md: mark Tasks 1-3 with their verified status, leave Tasks 4-5 as Not Started, and record files changed, commands run with actual results, and decisions made.
- Set "Next Recommended Action" to the start of Task 4.
- Leave changes uncommitted (or: commit them to the current branch with a clear WIP message).
- Report what was done, what remains, and anything I should review before the next session.
```

**Pause at a checkpoint after every task** (for your review):

```markdown
After each task, stop and report your results. Wait for me to say "continue" before starting the next one.
```

**Stop right now** (mid-session):

```markdown
Pause here. Finish or safely revert the task in progress, update PLAN.md so it reflects the verified current state (mark the interrupted task In Progress or Blocked with notes on what's done and what's left), set the next recommended action, and summarize where things stand. Do not start any new tasks.
```

**Resume later** with a new stopping point (use [Prompt 3](#3-resume-a-session) for a plain resume):

```markdown
Read AGENTS.md and PLAN.md, then follow the Session Recovery procedure and re-verify Task 3.

Continue with Tasks 4 and 5. Stop after Task 5, update PLAN.md, and report.
```