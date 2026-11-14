---
name: create-pr
description: Open a pull request for the current branch in the Iris repo. Asks all its questions up front (target branch, uncommitted changes, which tests to run, whether to confirm before pushing, issue and AI contribution details), then updates the branch with the target branch (merge, never rebase), resolves conflicts (pausing only when a conflict needs a decision), runs the chosen tests, writes the description from .github/pull_request_template.md, checks it against .github/scripts/pr_policy.py, then pushes and opens the PR. Never merges the PR. Use when the user asks to create, open or raise a PR, or types /create-pr.
argument-hint: "[target-branch, e.g. main or feat/US-41-reserve-a-unit]"
---

# Create a pull request

Take the current working branch to an open pull request that passes the PR policy check.

**Remind the developer that this is not a review.** In the same message as the step 2
questions (a note, not a question), say in one or two lines: "Reminder: this skill opens the
PR; it doesn't review your work. It won't confirm the story is complete, that business rules
are followed, or that there are no bugs the tests miss, so make sure you've reviewed your
own code first."

**Ask up front, then run.** Every question the skill can ask in advance is asked in steps 2
and 3, before anything changes. After that, work through to the end without asking again,
except for the situations in "When to stop anyway" below. The developer should be able to
answer the questions and walk away.

**Hard rules**

- Never merge the pull request: no `gh pr merge`, no merge button, no `git merge` of the
  working branch into the target, no push to the target branch. The PR stays open for review.
- Update the working branch with a **merge commit** (`git merge origin/<target>`). Never
  rebase, squash, amend or force-push: pushed commits are never rewritten.
- Never resolve a conflict that needs a judgement call on your own (step 6).
- Never skip hooks (`--no-verify`).

**When to stop anyway** (even in automatic mode)

- A merge conflict needs a decision (step 6).
- The merge refuses to start (for example, an untracked file would be overwritten).
- A test or check fails (step 7), except a timeout in a file the PR does not touch that
  passes when rerun alone.
- The PR policy check fails in a way the up-front answers do not cover (step 9).
- Anything unexpected: an error, a push rejected, `gh` failing. Report it and ask.

Never push or open the PR while one of these is unresolved.

## 1. Prepare (read only)

```sh
git rev-parse --abbrev-ref HEAD          # the working branch
git status --porcelain                   # uncommitted tracked changes (" M", "M ", ...) and untracked ("??")
git fetch origin
git branch -r --list 'origin/feat/*'     # candidate parent branches for the target question
gh auth status                           # whether the PR can be opened directly, and the token scopes
```

Adding the PR to the GitHub project needs the `project` scope on the `gh` token. If
`gh auth status` does not list `project` among the token scopes, tell the developer in the
same message as the step 2 questions (a note, not a question): "Your GitHub login can't add
PRs to projects yet. Run `! gh auth refresh -s project` before answering if you want the PR
added to the Iris project; otherwise I'll open it without the project and tell you at the end."
Re-check `gh auth status` after the answers come back.

If `$ARGUMENTS` names the target: check `git rev-parse --verify origin/<target>` and that it is
not the working branch, then also work out what step 3 needs (it can then be asked together
with step 2, in one call, if there are 4 questions or fewer in total).

## 2. Ask the run questions

One AskUserQuestion call, with only the questions that apply:

1. **Target** (only if `$ARGUMENTS` is empty), header "Target":
   "Which branch should this PR merge into?" Options: `main` and the story/epic branches
   that look like parents of the current one. Do not guess.
2. **Uncommitted changes** (only if tracked files are modified or staged), header "Changes":
   "`<n>` tracked files have uncommitted changes (`<first few paths>`). What should happen to them?"
   - **Commit them into this PR**: "Split into logical commits (one per task or area, tests
     with the code they cover), each with a subject that passes the commit-msg hook. You see
     the planned commits and approve them in the next round of questions, before anything is
     committed."
   - **Stash them, restore at the end**: "Left out of the PR and the tests; put back after the PR is opened."
   - **Stop**: "End the skill so you can deal with them yourself."
3. **Tests**, header "Tests": "Which tests should run before pushing and opening the PR?"
   1. **Quick checks (Recommended)**: "Lint, format and type checks, plus the unit tests
      for the areas this PR and the merge changed. Takes a few minutes and catches most
      problems before pushing. CI runs the full suite on the PR anyway."
   2. **Run all tests**: "Runs all the tests from CI locally on the merged code. Takes
      much longer."
   3. **Skip the tests**: "Only choose this if you have already run the full suite on
      this exact code, after merging the target branch and resolving any conflicts. Tests
      run before that do not cover what the merge brings in."

   If the target is known, add how many commits the merge will bring in
   (`git rev-list --count HEAD..origin/<target>`), so the developer knows whether an
   earlier test run still covers the code.
4. **Push and open**, header "Final step": "Once everything is ready, should I ask before
   pushing and opening the PR, or do it automatically?"
   - **Ask me first (Recommended)**: "You see the title, description and test results
     and approve before anything leaves your machine."
   - **Do it automatically**: "Push and open the PR as soon as the tests you chose and the
     policy check pass. It still stops for conflicts and failures."

If the developer picks **Stop**, end the skill.

## 3. Ask the PR detail questions

Now the target is known. Work out, without changing anything:

```sh
git log --oneline origin/<target>..HEAD --no-merges
git diff --name-status origin/<target>...HEAD
```

- the **ID** for the title: from the branch name (`feat/US-41-reserve-a-unit` → `US-41`) or
  the commit subjects;
- the **story and its tasks** on GitHub (see "Find the issues" below);
- the **AI level** to propose: the highest level among the changed source files' headers
  (first 10 lines), and which files are not "No substantial";
- changed source files **without an AI contribution header** (`pr_policy.is_source` and
  `has_declaration`);
- whether code changed with **no test change** (`pr_policy.needs_tests` / `is_test`).

Include uncommitted changes the developer chose to commit in all of these.

### Plan the commits

Only if the developer chose **Commit them into this PR** in step 2. List the tracked changes
(`git status --porcelain`, `git diff --stat`, `git diff --cached --stat`) and read the diffs,
then group the files into logical commits:

- **One commit per task or area.** Files that serve the same change go together; unrelated
  changes (a fix in one module, docs for another) go in separate commits.
- **Tests go in the same commit as the code they cover**, never in a commit of their own when
  that code is also in this plan. Test-only changes for code already committed get their own
  `test(...)` commit.
- **ID per commit**: the task ID when the change clearly belongs to one task. Match the
  module and files with the branch's existing commits for that task
  (`git log --format=%s origin/<target>..HEAD -- <path>`) and the story's sub-issues. If no
  task matches with certainty, use the PR's ID (the story, `SET-`, `FIX-`...).
- **Type and scope** from what changed: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`;
  the scope is the module or area (`reservations`, `household`, `skills`).
- **Subject**: `<ID> <type>(<scope>): <summary>`, lower-case summary, imperative, no full
  stop, as the commit-msg hook (`.githooks/commit-msg`) requires.
- **Order**: commits that others depend on first (model before service before API before
  screen); docs last.
- A file with changes for two different commits is rare. Put it in the commit it mostly
  belongs to and say so in the plan; never split hunks.

If everything is one small change, the plan is a single commit; that is fine.

### Find the issues

Each story is a GitHub issue titled `[US-xx] <name>` (epics `[ES-xx]`), and its tasks are
sub-issues titled `[T-xx.yy.z] <name>`. Get the owner/repo from `git remote get-url origin`.

1. Find the issue for the PR's ID by title:
   `gh issue list --search "<ID> in:title" --state all --json number,title,state`
   and keep the one whose title starts with `[<ID>]`.
2. If that is a **task** (`T-...`), get its parent story:
   `gh api graphql -f query='query { repository(owner:"<owner>", name:"<repo>") { issue(number:<n>) { parent { number title } } } }'`
3. Read the **story**: `gh issue view <story> --json title,body` for the user story and the
   acceptance criteria (the `### Acceptance criteria` checklist).
4. List its **tasks**:
   `gh api graphql -f query='query { repository(owner:"<owner>", name:"<repo>") { issue(number:<story>) { subIssues(first:50) { nodes { number title state } } } } }'`
5. Match each task ID in the commit subjects (`T-06.41.4 feat(...)`) to its sub-issue
   (`[T-06.41.4] ...` → `#517`). Also note `(#123)` references in commit messages. A task
   with commits in this PR is a **candidate** for "finished"; one without commits is not.
6. Map each acceptance criterion to the changes that address it (from the diff and commits),
   or mark it as not covered by this PR.
7. **Milestone**: read it from the story and the picked tasks
   (`gh issue view <n> --json milestone`). Use it if they all agree. If they differ, ask in
   step 3 which one (the story's first, "(Recommended)"). If none has one, the PR gets none.
8. **Project**: find the team's "Iris" GitHub project:
   `gh project list --owner <owner> --format json` and keep the one whose title is or
   contains "Iris" (if several match, ask in step 3). Note its title and number.

If no issue is found this way, fall back to `.plans/`, `docs/` and commit messages, and ask.

### Questions

Then one AskUserQuestion call with only the questions that apply (skip any you are certain about,
except the AI level and the tasks, which the developer always confirms). If more than four
apply, ask the rest in a second call straight after.

1. **Issue** (only if the story was not found with certainty), header "Issue": "Which issue does this PR
   `close`/`belong to` (into `main` it must close it)?" Options: the candidates you found;
   the developer types another number with Other.
2. **Tasks** (if the story has tasks), header "Tasks", `multiSelect: true`: "Which tasks of
   `<story>` does this PR finish? Into `main`, the ones you pick are closed when the PR
   merges." One option per candidate task: label `#<n> <T-ID>`, description its title and
   the commits that touch it. If there are more than four candidates, split them over two
   questions. Tasks not picked are listed as "in progress" in the description.
3. **AI level**, header "AI level": "Which AI contribution level for the PR description?"
   The three levels, your proposal first with "(Recommended)" and why (e.g. "5 of 7 changed
   files say 50% or more").
4. **Missing headers** (if any), header "Headers": "These changed files have no AI
   contribution line: `<paths>`. Which level should I add to them?" The three levels.
5. **No tests** (if code changed and no test did), header "No tests": "Code changed but no
   test file did. Which reason goes on the `No tests:` line?" Offer likely reasons (e.g.
   "refactor only, existing tests cover it", "configuration only"); Other for a custom one.
6. **Commits** (only if the developer chose to commit uncommitted changes), header "Commits":
   "I'll commit your uncommitted changes as these `<n>` commits, in this order. OK?"
   Put the whole plan in the first option's `preview` (each subject, then its files), e.g.:

   ```
   1. T-06.41.3 fix(reservations): refuse reserving on an expired listing
        backend/modules/reservations/services.py
        backend/modules/reservations/tests/test_reserve_service.py
   2. US-41 docs(reservations): document the expired-listing refusal
        backend/modules/reservations/README.md
   ```

   - **Use these commits (Recommended)**: "Committed as shown, before the merge."
   - **One commit for everything**: "A single commit with the first subject's ID and the most
     common type." Show that subject in its `preview`.
   - The developer can type changes with Other (e.g. "merge 2 into 1", "use T-06.41.4 for 1");
     apply them without asking again unless they are unclear.

From here, do not ask anything else unless "When to stop anyway" applies.

## 4. Uncommitted changes

- **Commit**: follow the plan the developer approved in step 3, one commit at a time, in order:

  ```sh
  git add -- <the files of this commit>      # only tracked files; never git add -A or git add .
  git commit -m "<subject>"
  ```

  End each message with the attribution lines your tool requires, if any. If something was
  already staged before the skill started, unstage it first (`git restore --staged .`) so
  each commit holds exactly its planned files. After the last commit, `git status --porcelain`
  must show no tracked changes; if one is left, stop and ask. If the commit-msg hook refuses a
  subject, fix the subject (not the hook) and commit again.
- **Stash**: `git stash push -m "create-pr: <branch>"` (tracked changes only). Restore it in step 11.

Untracked files stay where they are and are not part of the PR; mention them in the report.

## 5. Update the working branch

```sh
git merge --no-edit origin/<target>
```

- "Already up to date" or a clean merge → note which files came in
  (`git diff --stat ORIG_HEAD HEAD`), go to step 7.
- Conflicts → step 6.
- The merge refuses to start (e.g. "untracked working tree files would be overwritten") →
  stop and ask.

The commit-msg hook exempts merge commits, so Git's generated subject is fine.

## 6. Conflicts

List them with `git diff --name-only --diff-filter=U`. For each file read both sides
(`git show :2:<path>` ours, `git show :3:<path>` theirs, `git log --oneline -3 origin/<target> -- <path>`
for why the target changed it).

**Resolve yourself** only when the result keeps both sides' intent and nobody would decide
differently, for example:

- both sides added different imports, list entries, routes, tests or doc lines next to each other;
- one side only reformatted or renamed something the other side did not touch semantically;
- `frontend/src/shared/api/generated.d.ts`: take either side, then regenerate it after the
  merge (README "API types" commands) instead of hand-merging;
- lock files (`backend/uv.lock`, `frontend/pnpm-lock.yaml`) when the working branch also
  changed the manifest (`backend/pyproject.toml`, `frontend/package.json`): take the target's
  lock file, then re-run the package manager (`uv lock`, `pnpm install`) so the branch's
  manifest changes are locked again. If the branch changed the lock file **without** its
  manifest (a lock-only upgrade such as `uv lock --upgrade-package <name>`), ask instead:
  taking the target's version would silently drop that upgrade.

**Pause and ask the developer** (AskUserQuestion, all open conflicts in one call where
possible, each question standing on its own: file, what ours does, what theirs does, a
recommended option first) when:

- both sides changed the same logic, rule, validation, query or UI behaviour differently;
- Django migrations clash (two `0NNN_` files with the same parent): ask whether to add a merge
  migration (`makemigrations --merge`) or renumber the branch's unpushed migration;
- a file was deleted on one side and edited on the other;
- you are not sure. When in doubt, ask.

Offer choices like: keep ours, keep theirs, combine (show the combined code in `preview`),
or abort the merge (`git merge --abort`, restore any stash, then stop the skill).

After resolving every file: `git add <files>`, check no markers remain
(`git diff --cached --check` and a grep for `^<<<<<<<|^>>>>>>>`), then `git commit --no-edit`.
Summarise each resolution for the report.

## 7. Run the tests

Follow the step 2 answer. **Skip the tests** → go to step 8.

The Docker Compose stack must be up
(`docker compose ps --services --status running` lists `backend`, `db`, `azurite`); if it is
not, start it in the background with `docker compose up -d`. If the merge changed
`backend/uv.lock`, `backend/pyproject.toml` or the backend `Dockerfile`, run
`docker compose up -d --build backend` first.

The backend source is mounted into the container, so it sees the merged code. The
running frontend container only gets `src/` through `--watch` sync, so frontend checks
always use a fresh image of the merged checkout (`docker compose build frontend`, then
`docker compose run --rm --no-deps -T frontend ...`).

Run independent commands in parallel and long ones in the background.

### Full run

Run the checks from the `backend` and `frontend` jobs of `.github/workflows/ci.yml` that
can run locally. Before running, compare this list with the `run:` steps of `ci.yml` on the
merged code; if CI has gained a step that is not here and not under "Left to CI" below,
run it too if it can run in Docker, otherwise add it to the left-to-CI list in the report.

Backend:

```sh
docker compose exec -T -e DJANGO_SETTINGS_MODULE=iris.settings.test backend python -m pytest -m "not slow_expiry" --cov
docker compose exec -T backend ruff check .
docker compose exec -T backend ruff format --check .
docker compose exec -T backend mypy .
docker compose exec -T backend lint-imports
docker compose exec -T backend python manage.py makemigrations --check --dry-run
```

Production deployment check, only if `ci.yml` has the "Production deployment check" step
(it runs `manage.py check` against the production settings). Pass each variable from that
step's `env:` block with `-e` (they are synthetic CI values, not secrets):

```sh
docker compose exec -T -e DJANGO_SECRET_KEY=<from ci.yml> -e DJANGO_ALLOWED_HOSTS=<from ci.yml> ... backend python manage.py check --settings=iris.settings.production --deploy --fail-level WARNING
```

Frontend:

```sh
docker compose build frontend
docker compose run --rm --no-deps -T frontend sh -c "pnpm lint && pnpm format:check && pnpm typecheck && pnpm test:coverage && pnpm build"
```

API types and the policy checker:

```sh
docker compose exec -T -e PYTHONUTF8=1 backend python -B manage.py spectacular --format openapi-json --validate --fail-on-warn | docker compose run --rm --no-deps -T frontend pnpm gen:api --schema-stdin --check
docker compose run --rm --no-deps -T -v "$PWD/.github/scripts:/scripts" -w /scripts backend sh -c "ruff check --extend-ignore EXE002 . && ruff format --check ."
py -m unittest discover -s .github/scripts -p "test_*.py"
```

(`py` is the Python launcher on Windows; use `python3` elsewhere. The backend container only
mounts `backend/`, so the policy checker's Ruff run mounts `.github/scripts` itself; EXE002
is ignored because Windows bind mounts mark every file executable, as in the backend's Ruff
config. In Git Bash, set `MSYS_NO_PATHCONV=1` for that command.)

**Left to CI** (say so in the report): the `slow_expiry` photo test (a real five-minute
wait), `pip-audit` and `pnpm audit`, `pnpm test:api` (some of its tests start the backend's
`backend/.venv` Python, which the frontend container does not have), secret scanning
(gitleaks), the ZAP baseline scan, and SonarQube.

### Quick checks

Work out the changed files: the PR's diff plus whatever the merge brought in.

```sh
git diff --name-only origin/<target>...HEAD
git diff --name-only ORIG_HEAD HEAD      # only if step 5 merged new commits
```

Run only what applies (skip a block when no file in it changed):

- **Backend `.py`, `backend/pyproject.toml` or `backend/uv.lock` changed** (`backend/`):
  - `docker compose exec -T backend ruff check <changed .py files, paths relative to backend/>`
    (skip when no `.py` file changed)
  - `docker compose exec -T backend ruff format --check <same files>` (skip when no `.py`
    file changed)
  - `docker compose exec -T backend mypy .` (whole project: types cross files)
  - `docker compose exec -T backend lint-imports`
  - Pytest, chosen as follows (modules depend on each other, so testing only the touched
    folder misses breakage in the modules that call it):
    1. **Whole backend suite** if any of these changed: `modules/accounts/`, `modules/rules/`,
       `modules/stores/` (nearly every module depends on them), `backend/iris/`,
       `backend/adapters/`, `backend/conftest.py`, `backend/pyproject.toml` or `backend/uv.lock`.
       Also if steps 2 and 3 below add up to more than half of the modules.
       Run the full-run pytest command (without `--cov`) and skip the rest of this list.
    2. **Touched modules**: `backend/modules/<m>/...` → `modules/<m>/tests`.
    3. **Modules that use a touched module**: for each touched module `<m>`, find who imports it
       (run in `backend/`):
       `grep -rlE "(from|import) modules\.<m>([ .]|$)" modules tests --include=*.py`
       Each hit `modules/<x>/...` adds `modules/<x>/tests`; each hit in `tests/` adds that test
       file. One level of dependents is enough.
    4. **Changed test files** anywhere in `backend/`, including `backend/tests/`.

    Run them together in one command:
    `docker compose exec -T -e DJANGO_SETTINGS_MODULE=iris.settings.test backend python -m pytest -m "not slow_expiry" <test dirs and files>`
    In the one-line summary, name the dependent modules that were added and why
    (e.g. "households: imports listings").
- **Models or migrations changed** (`models.py`, `migrations/`):
  `docker compose exec -T backend python manage.py makemigrations --check --dry-run`
- **Frontend changed** (`frontend/`): build the image, then in one run:
  `pnpm lint && pnpm format:check && pnpm typecheck && pnpm vitest related --run <changed files under src/, relative to frontend/>`.
  If `package.json`, `pnpm-lock.yaml` or `vite.config.ts` changed, run `pnpm test` (all
  Vitest tests) instead of `vitest related`.
- **Any backend `.py` under `backend/modules/`, `backend/iris/` or `backend/adapters/`
  changed, or `frontend/src/shared/api/generated.d.ts` changed**: the API types check from
  the full run. Schema changes can come from services, models or settings, not only from
  `api/` folders, and the check is quick.
- **Settings changed** (`backend/iris/settings/`): the production deployment check from the
  full run.
- **Policy checker changed** (`.github/scripts/`): its Ruff and unittest commands from the
  full run.

Say in one line which checks you picked (no question, just keep going). Afterwards, note
what ran and what was left to CI (at least the full pytest suite with coverage,
`pnpm build`, any block skipped above, and the "Left to CI" list of the full run).

### If anything fails

First, check whether it is a timing failure in a test the PR does not touch. Some tests
(for example the frontend page tests that render the whole app and type into forms) time out
when the machine is busy running many tests at once, and pass when run alone.

A failure counts as a **timing failure** only when both are true:

- it is a timeout: Vitest's `Test timed out in <n>ms`, a Testing Library `findBy*` / `waitFor`
  giving up (`Unable to find ...` after waiting), or pytest's `subprocess.TimeoutExpired`;
- the failing test file is not in the PR's diff or the merge's changes
  (`git diff --name-only origin/<target>...HEAD` and, if step 5 merged new commits,
  `git diff --name-only ORIG_HEAD HEAD`).

For each such file, rerun it once on its own:

- frontend: `docker compose run --rm --no-deps -T frontend pnpm vitest run <file>`
- backend: `docker compose exec -T -e DJANGO_SETTINGS_MODULE=iris.settings.test backend python -m pytest -m "not slow_expiry" <file>`

If it passes alone, count it as passing and keep going without asking. Note it for the
description: "How it was tested" names each such file, the timeout seen in the full run, and
that it passed when rerun alone. Mention it in the report too.

Anything else is a real failure: a timeout in a file the PR or the merge touches (the change
may have made it slower), any other kind of error, or a file that still fails when run alone.
For those, stop, in either mode:

- Report the failing command and the relevant output.
- If the failure comes from the merge (the target changed the code involved), propose a fix
  and ask before changing code; a fix is a normal commit with a valid subject, tests in the
  same commit as the code they cover.
- Do not push or open the PR while tests fail unless the developer explicitly says to. If they
  do, list the failing tests in "How it was tested".

## 8. Write the title and description

Use the step 3 answers.

**Title**: `[PR] <ID>: <summary>` (regex in `pr_policy.TITLE`). Several IDs are joined
with `, `. Allowed IDs: `T-05.33.3`, `SET-17`, `FIX-03`, `US-17`, `ES-01`.

**Issue links** (`check_link`), one per line at the top of the body:

- Target is `main` (the default branch): `Closes #<task>` for each task picked in step 3.
  Add `Closes #<story>` only if every task of the story is now picked or already closed (or the
  story has no tasks); otherwise write `Part of #<story>`, since the story is not finished.
  At least one `Closes` line is required; `Refs` / `Part of` alone does not count.
- Any other target: `Part of #<story>`, then `Part of #<task>` for each picked task. GitHub
  only closes issues from PRs into the default branch.

**Body**: follow `.github/pull_request_template.md`, with the comments removed, plus a
"Stories and tasks" section before "What changes":

```markdown
Closes #<task>
Closes #<task>
Part of #<story>          (or Closes #<story> when every task is done)

## Stories and tasks

**<US-ID> <story title>** (#<story>)

- [x] #<n> <T-ID> <task title> (finished here)
- [ ] #<n> <T-ID> <task title> (in progress / not in this PR)

## What changes

<what and why, a few lines, from the commits and the diff>

Acceptance criteria covered (from #<story>):

- <criterion>: <how this PR meets it, naming the main files or behaviour>
- <criterion>: not covered by this PR

## How it was tested

<tests added or changed, including at least one error or edge case, then the step 7 result:
full run (results), quick checks (what ran; the full suite is left to CI), or skipped (the
skill did not re-run them; the developer's earlier run on the merged code is relied on).
If step 7 found timing failures in files the PR does not touch, name each file, the timeout,
and that it passed when rerun alone>

## AI contribution

Level: <the level chosen in step 3>

AI-assisted files:

- `path/one.py`
- `path/two.tsx`

## Checklist

- [x] Every source file I added or changed starts with its AI contribution line
- [ ] `AI_USAGE.md` updated if this is a substantive feature built with AI help
- [ ] The issue links this pull request and its tests

---

Opened with the `create-pr` skill (`.claude/skills/create-pr`).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Always end the body with those last two lines, so reviewers know how the PR was made.

Rules from `pr_policy.py`:

- Exactly one level string may appear in the AI contribution section: `No substantial
  AI-generated code`, `Below 50% AI-generated`, `50% or more AI-generated`.
- Unless the level is "No substantial", list at least one **changed** path in backticks
  or as `- path` lines. List each changed file whose header is not "No substantial".
- If code under `backend/`, `frontend/src/`, `frontend/scripts/`, `tools/` or
  `.github/scripts/` changed and no test file did, add the line `No tests: <reason from step 3>`.
- Tick checklist items only when true (check `AI_USAGE.md` in the diff).

## 9. Check against the PR policy

If step 3 found files without an AI contribution header, add the chosen level in their first
10 lines (`# AI contribution: <level>` or the file type's comment syntax) and commit it
(`<ID> chore(<scope>): add AI contribution header`).

Write the body to the scratchpad directory and run:

```sh
py .claude/skills/create-pr/scripts/check_pr.py --base <target> --title "<title>" --body-file <scratchpad>/pr-body.md
```

It runs `pr_policy.evaluate` on the local diff. Fix every `FAIL` from the step 3 answers and
re-run until it passes. If a fix needs a decision those answers do not cover (e.g. a header
missing on a file the merge brought in), stop and ask.

## 10. Push and open

Follow the step 2 answer:

- **Ask me first**: show the target, title, full body, number of commits and the test
  summary, and ask for confirmation. On no, restore any stash from step 4 (`git stash pop`,
  as in step 11), then stop. Nothing has been pushed; tell the developer that the commits
  from step 4, the merge commit and any header commit are still on the local branch.
- **Do it automatically**: go ahead, but only if step 7 passed (or was skipped/quick as
  chosen) and step 9 passed.

```sh
git push -u origin HEAD
```

Open the PR:

The PR is assigned to the developer running the skill (the account `gh` is signed in as),
put in the story's milestone, and added to the Iris project (all from step 3).

- If `gh` is available (`gh auth status` succeeds):
  `gh pr create --base <target> --head <branch> --title "<title>" --body-file <scratchpad>/pr-body.md --assignee @me --milestone "<milestone title>" --project "<project title>"`
  Leave out `--milestone` when there is no milestone, and `--project` when the token lacks
  the `project` scope or no project was found.
  If `gh pr create` fails because of the milestone or project, run it again without that flag,
  so the PR still opens, then try adding it afterwards.
  Then check it all took: `gh pr view <number> --json assignees,milestone,projectItems`, and
  fix what is missing:
  - assignee: `gh pr edit <number> --add-assignee @me`
  - milestone: `gh pr edit <number> --milestone "<milestone title>"`
  - project: `gh project item-add <project number> --owner <owner> --url <PR url>`
  If a fix also fails, say so in the report instead of stopping.
- Otherwise, give a link the developer opens to create it, with title, body, milestone and
  project URL-encoded:
  `https://github.com/<owner>/<repo>/compare/<target>...<branch>?expand=1&title=<title>&body=<body>&milestone=<milestone title>&projects=<owner>/<project number>`.
  Remind the developer to check the milestone and project on the page before creating it.
  Read the owner/name from `git remote get-url origin`. If the URL is over ~7,000 characters,
  give the link without `body` and print the body for the developer to paste. Without `gh`
  the skill cannot tell who the developer is on GitHub, so remind them to assign themselves
  (Assignees → "assign yourself") after creating it.

### Link the PR on the issues it closes

Once the PR exists, put a line at the **top of the description** of each issue named in a
`Closes #<n>` line of the body (the picked tasks, and the story when it is closed too), so
anyone opening the story or task sees straight away which PR closes it:

```
This item is closed in this PR: <PR url>
```

followed by a blank line, then the issue's existing description unchanged. Do it with a
file, never by retyping the description:

```sh
gh issue view <n> --json body --jq .body > <scratchpad>/issue-<n>.md
# write <scratchpad>/issue-<n>-new.md: the line, a blank line, then issue-<n>.md as it is
gh issue edit <n> --body-file <scratchpad>/issue-<n>-new.md
```

- Use the PR's full URL (e.g. `https://github.com/<owner>/<repo>/pull/691`). GitHub shows
  it as a link with the PR title and its open/merged state.
- Only `Closes` issues get the line. `Part of` issues (a story that stays open, or anything
  when the target is not `main`) do not, because this PR does not close them.
- If the description already has a `This item is closed in this PR:` line, replace that line
  instead of adding a second one (the PR may have been reopened as a new one). If it already
  has this PR's URL, leave the issue as it is, for example when the skill is run again.
- Change nothing else in the description. Read the issue back afterwards
  (`gh issue view <n> --json body`) and check the rest is identical.
- Do not post it as a comment.
- If an edit fails, say so in the report instead of stopping; the PR is already open.
- Without `gh`, list the issues in the report and ask the developer to add the same line to
  the top of each description after creating the PR.

## 11. Restore and report

If step 4 stashed changes: `git stash pop`. If it conflicts, leave the stash in place and tell
the developer (`git stash list`).

Tell the developer: the PR link (or the create link), the target branch, the milestone and
project it was added to (or why not), which issues it
closes or is part of (and which got the "This item is closed in this PR" line in their description), how conflicts were
resolved, the test results (and what was skipped or left to CI), untracked files left out,
and that the PR is open and **not merged**. Remind them that the `pr-policy`, `commit-policy`
and CI checks run on GitHub, and that the PR is merged with "Create a merge commit" by a
reviewer, not by this skill.
