<!-- AI contribution: 50% or more AI-generated -->

# Time to post a listing (US-33, T-05.33.5)

**Status:** prepared on 2026-10-30; sessions planned for 2026-10-30 to 2026-11-01.
Fill in the [results](#results), [observations](#observations-and-fixes) and
[outcome](#outcome) after the three sessions.

## What we check

US-33 (#491) asks that store staff post a listing from their phone "in under a minute
so that posting fits my shift". Its acceptance criterion: **median time to post 60 seconds
or less with three test users**. The persona is Karim, a shift supervisor at a partner
grocery: busy counter, one hand free (personas.md).

T-05.33.5 (#496) is done when the median is 60 s or less, **or** when issues are filed
for what slows people down.

## Set-up

The posting form (T-05.33.4) needs a signed-in store worker, and sign-in arrives with
US-01. Until then the study uses a **preview API** that answers as a store worker, serves
the real categories (SET-12 seed), accepts every listing **without saving it** and times
each run. It only listens on `127.0.0.1` and holds no personal data.

1. In `frontend/`, start the preview API (port 8000, where Vite already sends `/api`).
   It needs the backend's virtual environment (`backend/.venv`) to read the categories.

   ```powershell
   pnpm usability:preview          # or: node scripts/usability/preview.mjs
   ```

   If port 8000 is taken, stop the Docker backend (`docker compose stop backend`) first.

2. In a second terminal, in `frontend/`, start the app: `pnpm dev` (or
   `.\node_modules\.bin\vite`).
3. In Chrome, Edge or Opera, open DevTools (F12), turn on the device toolbar
   (Ctrl+Shift+M) and set **Dimensions: Responsive, 360 × 800** (the smallest phone of
   NFR-02). Keep the app in French, its default.

Participants use the mouse as their finger and the keyboard to type; see
[limitations](#limitations).

## Participants

Three people who did not build the form, coded **P1, P2 and P3**. Record no names, ages
or other personal details here or anywhere in the repository (PRV-10). Before starting,
tell each person what is timed (posting one listing), that nothing about them is recorded,
and that they can stop at any time; go on only with their verbal agreement.

## Scenario card

Read it aloud, then leave it in front of the participant. Every value is made up.

> Vous êtes responsable de quart dans une épicerie partenaire de B.A.D.R. Il vous reste
> **5 pains de la veille**. Publiez-les dans Iris pour que les foyers puissent les
> réserver. Ils sont bons **jusqu'à demain**. La cueillette se fait **aujourd'hui entre
> 16 h et 18 h**.

(You are a shift supervisor at a B.A.D.R. partner grocery. You have 5 day-old loaves left.
Post them in Iris so households can reserve them. They are good until tomorrow. Pickup is
today between 4 and 6 p.m.)

A correct post has category **Boulangerie**, quantity **5**, best before **tomorrow**,
pickup today 16:00 to 18:00 (the defaults), any title, and the safety box ticked. The
preview checks the category, quantity and best-before date of every post.

## Procedure, for each participant

1. Read the scenario card; answer questions about the situation, not about the screen.
2. When they are ready, open `http://localhost:5173/store/listings/new?participant=P1`
   (`P2`, `P3` for the others). The preview prints `P1: form loaded, the clock is running`.
3. Say « Allez-y ». Do not help unless they are stuck for 30 seconds; note any help.
4. The clock stops when the post is accepted (« Offre publiée »); the preview prints the
   run, its time, whether it matches the scenario, and the median so far. Errors shown by
   the form do not stop the clock: fixing them is part of the time.
5. Ask: « Qu'est-ce qui vous a ralenti? » (What slowed you down?) and note the answer in
   [observations](#observations-and-fixes).

A stopwatch from « Allez-y » to « Offre publiée » is the backup if the preview fails.
To try the set-up yourself first, open the page with `?participant=practice` (or no code):
practice runs are listed but never counted.

## How the timing works

`frontend/scripts/usability/` holds the preview (`preview-api.mjs`, started by
`preview.mjs`) and the timing rules (`runs.mjs`), with unit tests.

- The page address carries the participant code, and the browser sends it with every API
  call (`Referer`), so each person has their own clock.
- A run starts at the first category request of that participant's page (the form
  appearing) and ends when their listing is accepted. Reloading the page (F5) restarts
  the clock: a full load always asks who is signed in (`/api/me/`), and the preview prints
  `page reloaded, the running clock was dropped`. The form also re-reads the categories
  when the browser comes back into view; that does not restart the clock.
- So if a page was opened too early, reload it when the participant is ready. During a
  session, stay in the browser: the app asks again who is signed in after 5 minutes, so
  switching away and back in a run that long would restart its clock (the preview prints
  it).
- **Only each participant's first attempt counts**: the target is about posting during a
  shift, and first use is the cautious measure. Later attempts are listed to show learning.
- Runs are saved, one JSON line each, to `frontend/usability-runs.jsonl` (ignored by Git).
  Afterwards, `pnpm usability:report` prints the table and median for this document.

## Results

_To fill in: paste the output of `pnpm usability:report`._

| Participant | Attempt | Time to post (s) | Matches the scenario | Counted |
| --- | --- | --- | --- | --- |
| P1 | 1 | | | Yes |
| P2 | 1 | | | Yes |
| P3 | 1 | | | Yes |

Median: **_ s** (target 60 s).

Help given, if any: _

## Observations and fixes

_One row per thing that slowed someone down or caused an error. Fix small problems in the
form (and link the commit); file an issue for the rest._

| What happened | Seen with | Fix or issue |
| --- | --- | --- |
| | | |

## Outcome

_Tick one when the results are in._

- [ ] Median 60 s or less: US-33's time-to-post criterion is met.
- [ ] Median above 60 s: issues filed for the slowdowns above (links in the table).

## Limitations

- **Not a real phone.** The owner chose the browser's phone view on a PC (2026-10-29):
  a mouse instead of a thumb, a physical keyboard instead of the phone's, no gloves.
  Typing the title is probably faster than on a phone, so a real phone may take longer;
  repeat the check on phones once staging exists.
- **Preview API.** Answers are instant and nothing is saved; the real API adds network
  time and the US-34 safety checks.
- **Three people, not store staff.** Enough for the acceptance criterion, not for
  statistics. Their first use is measured, so regular staff should be faster.
