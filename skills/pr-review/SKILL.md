---
name: pr-review
description: "Use only when reviewing a GitHub PR by submitting one GitHub review: inline comments on specific findings, plus a summary, as REQUEST_CHANGES when findings exist or APPROVE when none exist."
---

# PR Review Skill

Use this skill only to review a GitHub pull request by submitting a real GitHub PR review.

The skill's job is exactly:

1. inspect the PR
2. identify specific actionable findings introduced by the PR
3. leave inline comments only for those specific findings
4. include a top-level review summary only when there are findings or real requested question responses to answer
5. submit the review as:
   - `REQUEST_CHANGES` if there are any inline finding comments
   - `APPROVE` if there are no inline finding comments

Do **not** use this skill for a Discord-only review report. Do **not** use it to summarize a PR without submitting the GitHub review. Do **not** create a separate pile of top-level comments like a raccoon sorting trash.

## Required GitHub auth

Configure your own reviewer account before use. Honor an existing job-local `GH_CONFIG_DIR`; otherwise use your own CLI config. Verify identity before every review:

```bash
gh auth switch --user <your-github-login>
gh api user --jq .login
```

Do not assume the active `gh` account is already correct.

## Input

The review target should be a GitHub PR:

- a GitHub PR URL
- `org/repo#123`
- a PR number when already inside the target repo

If the user provides extra review instructions, follow them unless they conflict with higher-priority Catty/workspace rules.

## PR setup

1. Identify the repository, PR number, base branch, and PR URL.
2. Clone the repository for review under `/tmp`, using a folder name that includes the repo and PR number:

```bash
gh repo clone <owner/repo-or-url> /tmp/<repo-name>-pr-review-<number>
cd /tmp/<repo-name>-pr-review-<number>
gh pr checkout <number-or-url>
```

Use your own repository and an isolated checkout; do not disturb another agent's or human's work.

3. Read the project instructions and README before reviewing code:
   - `AGENTS.md` from the repo root, if present
   - nested `AGENTS.md` files relevant to touched paths, if present
   - `README.md`, if present
4. Inspect the PR metadata and CI/check status. You do not need to mention CI in the review unless it explains a finding, but use it as context.
5. Run the current package manager's install command before reviewing checked-out PR/local changes, unless doing so would be destructive or obviously inappropriate:
   - `bun install` when `bun.lock`/`bun.lockb` exists
   - `pnpm install` when `pnpm-lock.yaml` exists
   - `npm install` when `package-lock.json` exists
   - `yarn install` when `yarn.lock` exists
   - language-specific equivalent if obvious from the repo
6. Read relevant nearby source, tests, schema/migrations, docs, and call sites. Do not review a diff in isolation when the bug depends on surrounding behavior.

## What counts as an inline finding

Leave an inline comment only when all of these are true:

1. The issue meaningfully affects correctness, performance, security, reliability, or maintainability.
2. The issue is discrete and actionable.
3. Fixing it fits the rigor level of the repository.
4. The issue was introduced by this PR, not pre-existing.
5. The PR author would likely fix it if made aware.
6. The issue does not rely on unstated assumptions about intent or deployment.
7. The affected code path or caller is identifiable, not speculative hand-waving.
8. The issue is not clearly an intentional behavior change.

Prefer no inline comments over weak comments. Ignore trivial style, formatting, naming, typos, and preference nits unless they hide a real bug or violate documented standards.

## Review priorities

Always review whether the PR follows KISS: is there a simpler, clearer way to solve the actual problem?

Do **not** encourage extra types, wrappers, or helper functions just for the sake of splitting code up. Most one-off logic can stay inline unless it needs reuse, export, independent testing, or a complexity boundary.

Prefer deterministic type references over manually maintained type files. Examples:

- `ReturnType<typeof fn>` for normal inferred return shapes when appropriate
- `RouterOutputs["router"]["procedure"]` for tRPC output shapes

A standalone types file that must be updated in parallel with implementation is usually a smell unless the type is a real domain contract.

You may ask questions about design decisions, but be sparse. Assume the author has thought through the shape unless the diff or surrounding code shows a concrete simpler path or hidden risk. Give advice only when it is truly needed.

## Inline comment rules

- One inline comment per distinct finding.
- Attach the comment to the shortest useful diff range, ideally 1–5 lines and rarely more than 10.
- Use `line` + `side`:
  - `RIGHT` for added/current lines
  - `LEFT` for deleted/base lines
- Avoid `position`; it is a diff offset, not a file line number.
- Verify every target line is commentable in the PR diff before submitting.
- Each comment body should start with a priority-tagged title, then one short paragraph:
  - `[P0]` drop everything; blocks release/ops/major usage, broadly triggered
  - `[P1]` urgent; should be fixed next cycle
  - `[P2]` normal; should be fixed eventually
  - `[P3]` low; nice-to-have but still a real issue
- Clearly state the scenario/input/environment required for the bug.
- Be matter-of-fact. No flattery. No accusatory nonsense. No “great job”.
- Do not include code blocks longer than 3 lines.
- Use ```suggestion blocks only for concrete replacement code, preserving exact leading whitespace.

Example inline comment body:

```text
[P2] Guard the missing guild config path

When this runs for a guild that has no config row yet, `config.settings` throws before the fallback can apply, so first-time setup fails instead of creating defaults.
```

## Top-level review response

For `REQUEST_CHANGES`, include a top-level review response via `--body-file`. This body is submitted as part of the same review, not as a separate PR comment.

For `APPROVE` reviews with no findings and no real question responses requested, leave no body at all — just approve it. Do not post a "No findings" essay, do not answer boilerplate questions nobody actually asked, and do not add a separate PR comment. If the user/repo explicitly asked specific review questions that need answers, include a concise approval body answering only those real questions.

When a body is needed, use:

```markdown
## Findings

- [P2] Concise title — `path/to/file.ts:123`
  Short summary of the finding. Full details still belong in the inline comment on the exact diff line.

## Overall correctness

patch is incorrect — Brief 1–2 sentence explanation.

## Best-practice answers

- Could we fix up everything? Yes/No, based on whether the review found actionable findings.
- Is this the most optimal implementation? Yes/No, based on the reviewed diff and surrounding code.
- Do we have enough tests? Yes/No, based on what was verified.
- Is there a better way to do this that fixes the issue everywhere instead of applying a single-area patch? No/Yes, based on the reviewed approach.
- Are there still any remaining questions? No/Yes, based on what remains uncertain.
```

Do not use a boilerplate approval body for no-finding reviews. Inline comments remain the source of detailed, line-specific feedback; the top-level body is for findings summaries or real requested question responses only.

## Submit exactly one PR review

Use the bundled helper to submit one review with batched inline comments and a summary. Resolve `<skill-directory>` to this SKILL.md file's parent directory; do not run the placeholder literally. Requires Python 3.10+, Git, and authenticated `gh`. Inspect `--help` first. Never include credentials in review files.

Resolve repo and PR:

```bash
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
pr=$(gh pr view --json number --jq .number)
```

Verify commentable lines:

```bash
gh api "repos/$repo/pulls/$pr/files" --paginate --slurp
```

### If findings exist: REQUEST_CHANGES

Write `/tmp/pr-inline-comments.json` as a JSON array:

```json
[
  {
    "path": "src/example.ts",
    "line": 123,
    "side": "RIGHT",
    "body": "[P2] Concise title\n\nWhen this specific condition happens, this introduced change breaks the affected behavior."
  }
]
```

Write `/tmp/pr-review-summary.md` with the full top-level review response, then dry-run and submit:

```bash
<skill-directory>/bin/submit-inline-review.py \
  --repo "$repo" \
  --pr "$pr" \
  --event REQUEST_CHANGES \
  --comments-file /tmp/pr-inline-comments.json \
  --body-file /tmp/pr-review-summary.md \
  --dry-run

<skill-directory>/bin/submit-inline-review.py \
  --repo "$repo" \
  --pr "$pr" \
  --event REQUEST_CHANGES \
  --comments-file /tmp/pr-inline-comments.json \
  --body-file /tmp/pr-review-summary.md
```

### If no findings exist: APPROVE

If there are no findings and no real question responses to include, approve with an empty body:

```bash
<skill-directory>/bin/submit-inline-review.py \
  --repo "$repo" \
  --pr "$pr" \
  --event APPROVE \
  --allow-empty
```

If the review request explicitly asks real questions that need answers, write a concise `/tmp/pr-review-summary.md` answering only those questions and pass `--body-file /tmp/pr-review-summary.md`.

## Verification

After submitting, verify the review and comments:

```bash
gh api "repos/$repo/pulls/$pr/reviews" --paginate --jq '.[] | {id, state, body, submitted_at}'
gh api "repos/$repo/pulls/$pr/comments" --paginate --jq '.[] | {id, path, line, side, pull_request_review_id, body}'
```

Report back on the requesting surface with only a short status: approved/no findings, or requested changes with count of inline findings. Mention the GitHub review body only if one was actually included. Do not paste the full review unless asked.

## Important behavior

- Do not submit more than one PR review for the same requested review pass.
- Do not submit standalone PR comments outside the review.
- Do not merge PRs from inside this skill. This skill submits reviews only; any merge requires a separate authorized workflow under your own workspace/repository rules.
- If the user asks for “no PR comments,” do not use this skill.
- If the project exposes an MCP/API surface, check whether changes require matching schemas, tools, docs, or validation.
- If the PR touches external APIs, verify current docs/OpenAPI/source before claiming endpoint or schema behavior.
- If setup hits macOS Keychain/keyring errors or hangs, stop and report it.
