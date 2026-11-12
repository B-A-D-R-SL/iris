<!-- AI contribution: 50% or more AI-generated -->
# Opening a pull request with the `create-pr` skill

The `create-pr` skill (`.claude/skills/create-pr/SKILL.md`) takes your branch to an open pull
request that passes the PR policy check. It never merges the PR.

## When to use it

When your branch is ready for review, into `main` or a story/epic branch.

## How it behaves

It asks all of its questions at the start, before it changes anything. After you answer, it
runs to the end on its own, so you can walk away. It only asks again if something needs a
decision (see "When it stops" below).

### First round: how to run

Only the questions that apply are asked.

| Question | Choices | Asked when |
| --- | --- | --- |
| Which branch should this PR merge into? | `main`, or a story/epic branch that looks like a parent of yours | You didn't name a target, e.g. `/create-pr main` |
| What should happen to your uncommitted changes? | Commit them into this PR, stash them and restore at the end, or stop | Tracked files have uncommitted changes |
| Which tests should run? | **Quick checks** (recommended): lint, format, types, plus tests for the areas you and the merge changed. **Run all tests**: everything CI runs. **Skip**: only if you already ran the full suite on the merged code. It also tells you how many commits the merge brings in. | Always |
| Ask before pushing, or do it automatically? | **Ask me first** (recommended): you see the title, description and test results before anything leaves your machine. **Automatically**: it pushes and opens once tests and the policy check pass. | Always |

If your GitHub login can't add PRs to projects, it also tells you to run
`gh auth refresh -s project` before answering.

### Second round: what goes in the PR

The skill finds your story on GitHub (from the branch name, e.g. `feat/US-41-...` → `[US-41]`),
its tasks, its milestone and the Iris project. Then it asks:

| Question | Choices | Asked when |
| --- | --- | --- |
| Which issue does this PR belong to? | The candidates it found, or type a number | The story couldn't be found with certainty |
| Which tasks does this PR finish? (pick several) | Each task with commits in the branch, e.g. `#517 T-06.41.4`, listed with its title and commits. Into `main`, the ones you pick close when the PR merges; the rest are listed as in progress. | The story has tasks |
| Which AI contribution level? | The three levels. It recommends the highest level in the changed files' headers, e.g. "51 of 52 files say 50% or more". | Always |
| Which level for files missing an AI contribution line? | The three levels; it adds the line and commits it | Changed files have no header |
| Why is there no test change? | Likely reasons, e.g. "refactor only, existing tests cover it", or your own | Code changed but no test file did |
| Which milestone? | The story's milestone first | The story and tasks have different milestones |

### Then it runs

1. **Update:** merges the target branch into yours with a merge commit, never a rebase.
2. **Tests:** runs the tests you chose in Docker.
3. **Description:** writes the title (`[PR] US-41: ...`) and description from the PR template:
   - issue links;
   - which acceptance criteria are covered;
   - test results;
   - AI-assisted files.

   It then checks them against `pr_policy.py` and fixes anything that fails.
4. **Push and open:** pushes, opens the PR assigned to you, and adds the milestone and the
   Iris project.
5. **Link the issues:** comments "This item is closed in this PR: <link>" on every task (and
   the story, if it closes too) named in a `Closes #` line, so anyone opening the issue sees
   which PR closes it.
6. **Report:** gives you the PR link, test results and anything it skipped.

### When it stops

- **Merge conflicts it can't settle alone:**
  - It resolves simple ones itself, such as two sides adding different imports or list
    entries.
  - When both sides changed the same logic, or migrations clash, it shows you both sides and
    asks: keep yours, keep theirs, combine, or abort the merge.
- **Test failures:**
  - A timeout in a file your PR doesn't touch is rerun on its own. If it passes, it's noted
    in the description and the run continues.
  - Any other failure stops the run and is reported. Nothing is pushed unless you say so.
- **Anything unexpected,** such as a rejected push, `gh` failing, or a PR already open for
  the branch.

It never merges the PR, rebases, force-pushes or skips commit hooks. A reviewer merges it
with "Create a merge commit".

## How to run it

In Claude Code, type `/create-pr` (or `/create-pr main`). Other agents: ask them to follow
the skill file.

## Setup

1. **Docker:** the Compose stack must be able to run (`docker compose up -d`). Tests run
   inside the containers.
2. **GitHub CLI:** install `gh` (Windows: `winget install GitHub.cli`, macOS:
   `brew install gh`), then sign in:

   ```sh
   gh auth login                # GitHub.com, HTTPS, sign in with a browser
   gh auth refresh -s project   # lets it add PRs to the Iris project
   gh auth status               # scopes should include repo, read:org, project
   ```

   Without the `project` scope the PR still opens, just without the project.
3. **Account permissions:** you need to be a member of the `B-A-D-R-SL` organization with
   write access to the `iris` repository, so you can push branches, open PRs and use the
   project.
4. **Python** (`py` on Windows, `python3` elsewhere): it runs the local policy check.

## Known issue on Windows

With `core.autocrlf=true`, `pnpm format:check` fails on every file (CRLF line endings) and
the skill stops. It is safe to continue; CI checks out LF.
