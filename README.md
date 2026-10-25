# Powder Peak: Ask a Ski Resort Database Questions in Plain English

**Purpose:** Powder Peak is a made-up ski resort. Its database tracks lifts, runs, guests, the passes they buy, every lift-gate scan, and ski/snowboard lessons. Staff can ask plain-English questions like *"Which lift was busiest in February?"* or *"Which instructor earned the most?"* and get a plain-English answer back. GPT writes and runs the SQL behind the scenes.

*By Ethan Collier*

![Schema](Powder%20Peak%20ERD.jpg)

8 tables, about 450 rows of fictional data (`schema.sql` + `data.sql`, prebuilt into `ski.db`):

| Table | What it holds |
|---|---|
| `lift` | Name, type (chair/gondola/tram/surface), seats, vertical rise, open today? |
| `run` | Name, difficulty (green → double black), length, groomed today?, and the lift that serves it |
| `pass_type` | Day Ticket, Season Adult/Youth/Senior, Night Ticket, and their prices |
| `guest` | Name, birth year, home state, skill level |
| `pass` | A guest's purchase of a pass type (some guests bought two) |
| `lift_scan` | Each time a pass is scanned at a lift (all of February 2026) |
| `instructor` | Name, ski or snowboard, hourly rate |
| `lesson` | Which instructor taught which guest, when, and for how many hours |

## How it works

1. The user types a question.
2. `app.py` sends the question plus the database schema (`schema.sql`) to GPT, which writes a SQLite query.
3. The query runs against `ski.db`, opened **read-only** so generated SQL can't change or delete data.
4. The question, the SQL, and the returned rows go back to GPT, which writes a short, friendly answer.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env     # or: export OPENAI_API_KEY=sk-...  (.env is git-ignored)
python app.py                           # ask questions interactively
python app.py --strategy zero_shot      # zero_shot | single_domain | cross_domain
python app.py --eval                    # run every question in questions.txt x 3 strategies -> results.md
```

Model defaults to `gpt-4o-mini`; override with `OPENAI_MODEL=...`. The app prints token usage and estimated cost when it finishes.

**Auto-grading:** most lines in `questions.txt` have a hand-written correct query after `||`. In `--eval` mode the app runs both queries and marks GPT ✅ if it returned the same rows (extra columns and different name formatting are allowed). This is the paper's *execution accuracy* metric, and it gives each strategy a score at the top of `results.md`.

## Prompting strategies

I followed the three settings from [Chang & Fosler-Lussier, *How to Prompt LLMs for Text-to-SQL* (2023)](https://arxiv.org/abs/2305.11853):

| Strategy | What GPT sees |
|---|---|
| **zero_shot** | The schema (as `CREATE TABLE` statements) + the question |
| **single_domain** | Schema + two solved question → SQL pairs written for *this* database |
| **cross_domain** | One solved question → SQL pair from a *different* database (a small library schema), then the ski schema + the question |

The paper found that the `CREATE TABLE` format was the best way to describe a schema (it's what this app uses). In-domain examples helped the most: Codex went from 73.1% to 81.3% on the Spider benchmark with 16 examples. Examples from other databases helped less, because they teach the SQL style but nothing about *your* tables.

**Results** (10 questions with an answer key, `gpt-4o-mini`):

| Strategy | Correct |
|---|---|
| zero_shot | **7**/10 |
| single_domain | **9**/10 |
| cross_domain | **10**/10 |

**What I noticed:** Adding *any* worked example made a big difference. Every zero-shot failure was a mistake in *finding its way through the tables*, not a SQL syntax error:
- It looked for `guest_id` in `lift_scan`, a column that doesn't exist (you have to go through `pass`).
- It matched `guest_id` directly to `pass_id`.
- It returned a lift ID instead of the lift's name.

Both example-based prompts showed GPT a multi-table `JOIN … GROUP BY … ORDER BY … LIMIT 1` that returns names, and both avoided those mistakes. The surprise was that cross-domain did as well as single-domain. The paper found in-domain examples clearly better. My guess: the "different database" example (`loan → book → author`) happens to have the same shape as the hardest questions here (`lift_scan → pass → guest`). With only 10 questions run once each, 9 vs 10 is within noise. GPT gives slightly different SQL each run.

## A question that worked

**Question:** Which guest rode lifts the most times, and how many rides was that?

This one is harder than it looks. It needs three tables (`lift_scan` → `pass` → `guest`), and some guests own two passes. Grouping by pass instead of by guest picks the wrong person (19 rides). The correct answer is Sophia Martinez with 31 rides.

GPT's SQL (single_domain):

```sql
SELECT g.first_name, g.last_name, COUNT(ls.scan_id) AS rides
FROM guest g JOIN pass p ON g.guest_id = p.guest_id
JOIN lift_scan ls ON p.pass_id = ls.pass_id
GROUP BY g.guest_id
ORDER BY rides DESC
LIMIT 1;
```

**Response:** "The guest who rode the lifts the most times is Sophia Martinez, with a total of 31 rides!" ✅

Single-domain and cross-domain both got it right. Zero-shot didn't: it wrote `SELECT guest_id … FROM lift_scan`, which fails with `no such column: guest_id`.

## A question that did not work

**Question:** Who skied the most vertical feet? *(zero_shot)*

```sql
SELECT g.first_name, g.last_name, SUM(l.vertical_ft) AS total_vertical
FROM guest g
JOIN lift_scan ls ON g.guest_id = ls.pass_id
JOIN lift l ON ls.lift_id = l.lift_id
GROUP BY g.guest_id
ORDER BY total_vertical DESC
LIMIT 1;
```

**Response:** "The guest who skied the most vertical feet is Wyatt Hansen, with a total of 44,900 vertical feet!" ❌

**Why it failed:** GPT skipped the `pass` table and joined `guest_id = pass_id`. The two IDs only line up by coincidence, so Sophia Martinez's rides on her second pass were never counted. It named the runner-up instead (the real answer is Sophia Martinez, 47,700 ft). This is the dangerous kind of failure: the query ran, the answer sounds confident and specific, and 44,900 ft really is Wyatt's total. Nothing in the answer hints that it's wrong.

**Single-domain got this one "right" for the wrong reason.** It named Sophia Martinez, but summed run *lengths* instead of lift vertical, counting every run on a lift for each ride. It reported 402,300 ft. My auto-grader first marked it correct because the answer key only checked the name, so I tightened the key.

### Another failure: "How busy is the mountain on weekends compared to weekdays?"

None of the three strategies answered this well. Zero-shot and cross-domain both filtered to weekends only (`HAVING day_of_week IN ('0','6')`) and then said *"the mountain tends to be busier on weekends"*, a comparison they had no weekday data for. The real answer is the opposite: about 14 scans per day on weekdays vs 8.5 on weekends. Both also swapped Saturday and Sunday (SQLite's `%w` uses 0 = Sunday, so Sunday had 31 scans, not 37). Single-domain fetched every day of the week but then said it "couldn't find specific comparisons."

## More examples

[`results.md`](results.md) has all 12+ questions, each run with all three strategies and auto-checked against the answer key in [`questions.txt`](questions.txt). A few more worth a look:
- **Do any expert skiers take lessons?** All three wrote correct SQL that returned no rows, but the answers said *"I couldn't find any information…"* instead of *"No."* That's my fault, not GPT's: my answer prompt says "if the results are empty, say you couldn't find the answer", which treats "zero matches" and "don't know" as the same thing.
- **Which lift had the most scans in February 2026?** Zero-shot found the right lift but called it "lift ID 2" and said 83 scans instead of 84. Its `BETWEEN '2026-02-01' AND '2026-02-28'` silently drops Feb 28, because `'2026-02-28 09:15:00'` sorts after `'2026-02-28'`.
- **Which runs can I ski today… black diamonds?** All three used `difficulty = 'black'` and left out `'double black'`. They were right only because both double-black runs happen to be on closed lifts.
- **What's the best lift for a beginner?** Each strategy defined "best" differently: every open lift with a green run, a list of lift + run pairs, or the lift with the most green runs (Pine Flat). All reasonable, none wrong, but they don't agree.

## What I learned

**How good is GPT at writing SQL?** Good at the routine work. 26 of 30 auto-checked runs were correct, and 19 of 20 once it had an example to copy. Filters, `COUNT`/`SUM`, `GROUP BY`, and three-table joins mostly came out right. It struggled with questions that need a definition the database doesn't contain ("busy", "best"). It also made small mistakes like a date range that's off by a day.

**Limitations.** GPT only knows what the schema tells it. It can't know that "today" means the `is_open` flag, or what "best" or "busy" should mean. Instead of asking for clarification, it picks an interpretation and answers confidently. A wrong query still produces a fluent, friendly answer, so **you can't tell from the answer alone whether it's right**. You have to check the SQL. That's why I added an answer key.

**Can GPT help as a software engineer?** Yes, as a fast first draft. Read-only database access, showing the SQL next to the answer, and automated checks against known answers all mattered more than prompt tweaks for making it trustworthy.

**Cost:** The full evaluation (12 questions × 3 strategies × 2 GPT calls = 72 calls) used **30,279 input + 2,626 output tokens on `gpt-4o-mini` ≈ $0.006**, less than a cent, or about $0.0002 per question answered. That's estimated from the per-token prices in `app.py`; OpenAI's usage page has the exact bill. Input outweighs output more than 10 to 1 because every call resends the whole schema. That's the first thing to trim for a bigger database or a pricier model.

## Going further: talking to *any* database

To make this work for an arbitrary database, I'd:
1. **Read the schema automatically** (SQLite `sqlite_master`, Postgres `information_schema`) instead of using a hand-written file.
2. **Send only the relevant tables.** Real databases have hundreds of tables, which won't fit in one prompt. The paper also found accuracy *drops* once prompts get too long (around 5,500 tokens for Codex).
3. **Include a few sample values per column.** This was the paper's best zero-shot setup (73.1% → 75.7%), and it shows GPT, for example, that `difficulty` uses `'double black'`, not `'expert'`.
4. **Retry on errors:** feed the SQL error back to GPT and let it fix the query.
5. **Ask a clarifying question** when the question is vague ("best", "busy") instead of guessing.
6. **Stay safe:** read-only credentials, row limits, query timeouts, and always showing the SQL.

## My own question

**Question:** Which lift do season pass holders ride the most? *(single_domain, asked interactively)*

```sql
SELECT l.name, COUNT(ls.scan_id) AS scan_count
FROM lift l
JOIN lift_scan ls ON ls.lift_id = l.lift_id
JOIN pass p ON p.pass_id = ls.pass_id
GROUP BY l.lift_id
ORDER BY scan_count DESC
LIMIT 1;
```

**Response:** "Season pass holders ride the Aspen Glade lift the most, with 84 scans recorded." ❌ (half right)

Aspen Glade is the right lift, but the query never filters to season passes. That needs one more join to `pass_type` and `WHERE pt.name LIKE 'Season%'`. So 84 is the count for *everyone*; season-pass holders account for 40 of them. The answer still says "season pass holders" as if it had filtered. The SQL shows otherwise, which is another case where only reading the SQL catches the mistake.

## Who did what

Solo project: **Ethan Collier** designed the database (all 8 tables, keys, and sample data), built the app, ran the experiments, and wrote this up.
