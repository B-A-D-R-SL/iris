# How We Work

## Team Organization

We will work collaboratively on Project Iris, with team members contributing to different features and user stories based on availability, skills, and project priorities.

Responsibilities will remain flexible, and everyone is encouraged to collaborate and help others when needed.

## Our Approach

Our main objective is to **complete user stories and progressively integrate them into a working version of Project Iris**.

We will create smaller tasks when necessary to organize the work, but the **user story remains our main unit of progress**.

Team members may work independently or collaborate on the same user story, depending on its complexity and requirements.

## Communication and Meetings

- **Weekly team meeting:** We will meet once a week to share progress, discuss upcoming work, identify blockers, and coordinate integration.
- **Ongoing communication:** Team members should communicate whenever they make meaningful progress, have questions, encounter blockers, or need assistance.
- **Collaboration:** Everyone is encouraged to support other team members and coordinate work whenever features depend on each other.
- **Stakeholder reviews:** We will review progress with B.A.D.R. when possible to gather feedback and confirm requirements.

Communication should remain simple and natural without unnecessary reporting requirements.

## Tasks and Project Board

We will use the **Project Iris** GitHub board to organize user stories, tasks, and progress.

The board will follow:

**Backlog → Ready → In Progress → In Review → Done**

User stories may be broken down into smaller tasks for implementation, testing, documentation, and integration.

Not every small action requires a separate issue. Tasks should be created when they help organize work or clarify responsibilities.

## Development Workflow

We will follow a common GitHub workflow:

1. Select an assigned or available user story or task.
2. Coordinate with other team members when needed.
3. Implement the functionality and relevant tests.
4. Open a pull request for review.
5. Address feedback and merge the changes.
6. Integrate the completed functionality into Project Iris.

Where to find the details:

- Commit message format, the pull request checks and the CI jobs: the [README](../../README.md) ("Commit hooks", "Pull requests", "Continuous Integration").
- Branch, commit and pull request rules in short, and opening a pull request with `/create-pr`: [CONTRIBUTING.md](../../CONTRIBUTING.md).
- What reviewers check: [review rules](review-rules.md) (eleven rules; CodeRabbit enforces them with eleven custom pre-merge checks in [`.coderabbit.yaml`](../../.coderabbit.yaml), eight as errors and three as warnings).
- Merging: the `main` ruleset requires four checks (`backend`, `frontend`, `pr-policy`, `commit-policy`) and one human approval. CodeRabbit's approval does not count as that review. Merge commits only, no squash. Repository admins can bypass the ruleset when merging, only for a check that fails by design or for a cause outside the pull request, never to skip the review, and with the reason posted on the pull request ([CONTRIBUTING.md](../../CONTRIBUTING.md#review-and-merge)).
- AI usage records: the wiki's [AI Usage](https://github.com/B-A-D-R-SL/iris/wiki/AI-Usage) pages; [AI_USAGE.md](../../AI_USAGE.md) lists the AI tools we use and points there; entries go only in the wiki.

## Iterations and Integration

Development will be organized into iterations, each containing a set of planned user stories.

Our focus during each iteration will be completing functional features that can be integrated into the overall application.

At the end of each iteration, we will review completed work, identify remaining tasks, and adjust priorities for the next iteration.

## Definition of Done

We use one Definition of Done, the one on the wiki's [Acceptance Criteria](https://github.com/B-A-D-R-SL/iris/wiki/Acceptance-Criteria) page. A user story is complete when:

- Every acceptance criterion is met.
- The unit-tests task and every build task are closed.
- Screens exist in French and English.
- CI is green, CodeRabbit comments are answered, and one teammate has given a substantive review.
- Pull requests and tests are linked in the issue.
- B.A.D.R. has confirmed the story works, recorded with the `signed-off` label on the issue. The label means B.A.D.R. confirmed it; do not add it without that confirmation.

## Documentation

Important decisions, changes, and meeting outcomes will be documented when necessary.

Technical decisions are recorded in `docs/adr/`. Meeting minutes are in the wiki; `docs/meetings/` only holds the note template.

Documentation should help the team understand and maintain the project without creating unnecessary administrative work.

**Our priority is collaboration, steady progress, and delivering a functional, integrated Project Iris.**