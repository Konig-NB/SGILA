# Grade 2 activities

All Grade 2 activities from **Grade2_FINAL_Complete_Spec_v2** now live in one file:

    api/grade2_activity_blueprints.py

It holds every activity for all five Grade 2 stories, in the same order as the
document:

| # | Activity | Per story |
|---|----------|-----------|
| 1 | Comprehension Questions | 5 |
| 2 | Match It! (4 pairs + 1 decoy) | 1 |
| 3 | Story Sequencer | 1 (5 events) |
| 4 | Visual Matching | 5 |
| 5 | Spelling | 5 |
| 6 | Fix the Mistake | 5 |

That is 22 activities worth 25 marks per story, for *A Dog's Life*, *A New Baby*,
*The School Shed Is on Fire*, *Dan's Bad Week* and *Spring Day Surprise*.

## Loading them

The activities are already loaded in `db.sqlite3`, so you can just start the app:

    python manage.py runserver

To reload them (after editing the blueprint file, or on a fresh database):

    python manage.py sync_grade2_activities

One story at a time:

    python manage.py sync_grade2_activities --story "Dan's Bad Week"

The command clears that story's old Grade 2 activities first and rewrites them,
so running it twice does not create duplicates. Grades 1, 3 and 4 are untouched.

## Editing an activity

Change the wording in `api/grade2_activity_blueprints.py`, then run
`sync_grade2_activities` again. Nothing else needs editing — the loader also
refreshes the older comprehension, sequencing, visual matching and spelling
tables so no screen disagrees with another.

## How each activity works

**Match It!** follows the v2 rules in the document. Four items on the left, five
on the right — the fifth is a decoy that matches nothing, so the last pair can't
be solved by elimination. The learner chooses all four matches and only then
checks, so there is no try-until-green guessing. The decoy is the last entry in
each `match_it(...)` right-hand list, marked with a `# decoy` comment.

**Spelling** uses whichever style the document sets for that story: fill the
missing vowel (*A Dog's Life*, *The School Shed Is on Fire*), unscramble the
letters (*A New Baby*, *Spring Day Surprise*), or choose the correct spelling
(*Dan's Bad Week*). Every question shows the matching picture from the story's
vocabulary sheet in `static/img/vocab_sheets/`.

**Fix the Mistake** shows a story sentence with one word swapped and gives three
words to choose from, exactly as listed in the document.

## Two migration fixes that came with this

These were already broken before the Grade 2 work, but they had to be fixed for
the activities to load on a fresh database:

- `0021_merge_20260917_1434.py` — the migration history had split into two
  branches that both built on `0017_merge_20260809_1203`, so `manage.py migrate`
  and `manage.py test` both refused to run. This merge has no schema changes; it
  just gives the graph a single leaf again.
- `0022_spellingactivity_image_url.py` — `SpellingActivity.image_url` existed on
  the model but had never been migrated. The bundled `db.sqlite3` happened to
  have the column, so the app ran, but a fresh `migrate` produced a table without
  it and 39 tests errored. The spelling activities store their picture there, so
  this one matters directly.

With both applied, `manage.py test api` runs: 58 tests, 4 failures, all four
pre-existing and unrelated to Grade 2 (curriculum seed scope, a stylesheet
check, Grade 3 visual matching, and a parent-dashboard route).

## Pictures

Each story has a vocabulary sheet of six panels in `static/img/vocab_sheets/`,
cropped with `#panel-1` to `#panel-6`, numbered left to right, top row first.
`picture_for()` in the blueprint file looks a word up on its story's sheet and
returns an empty string when there is no panel for it (the only one is *ball*
in *Dan's Bad Week*, which shows with no picture).
