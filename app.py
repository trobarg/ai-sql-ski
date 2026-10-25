"""
Natural-language interface to a ski resort database.

Flow: question -> GPT writes SQL (using the schema) -> run SQL on SQLite
      -> GPT turns the rows into a plain-English answer.

Three prompting strategies from Chang & Fosler-Lussier (arXiv 2305.11853):
  zero_shot      - schema + question only
  single_domain  - schema + a couple of solved examples from THIS database
  cross_domain   - schema + a solved example from a DIFFERENT database

Usage:
  export OPENAI_API_KEY=sk-...      (Windows PowerShell: $env:OPENAI_API_KEY="sk-...")
  python app.py                     # interactive: type questions
  python app.py --strategy zero_shot
  python app.py --eval              # run questions.txt with all 3 strategies -> results.md
"""

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).parent
DB_PATH = HERE / "ski.db"

# Optional: put OPENAI_API_KEY=sk-... in a .env file next to this script (git-ignored).
# A key exported in the shell takes precedence.
if (HERE / ".env").exists():
    for line in (HERE / ".env").read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and value.strip() and not line.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# USD per 1M tokens (input, output). Update if you switch models.
PRICES = {"gpt-4o-mini": (0.15, 0.60), "gpt-4.1-mini": (0.40, 1.60), "gpt-4.1-nano": (0.10, 0.40),
          "gpt-5-nano": (0.05, 0.40), "gpt-5-mini": (0.25, 2.00), "gpt-4o": (2.50, 10.00)}


# ---------- database ----------

def build_db(rebuild=False):
    if DB_PATH.exists() and not rebuild:
        return
    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript((HERE / "schema.sql").read_text())
    con.executescript((HERE / "data.sql").read_text())
    con.commit()
    con.close()


def run_sql(sql):
    # Read-only connection so a bad generated query can never modify the data.
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, cur.fetchall()
    finally:
        con.close()


SCHEMA = (HERE / "schema.sql").read_text()


# ---------- prompts ----------

SINGLE_DOMAIN_EXAMPLES = """\
Question: Which open lifts have more than 2000 feet of vertical?
SQL: SELECT name, vertical_ft FROM lift WHERE is_open = 1 AND vertical_ft > 2000;

Question: How many lessons has each instructor taught?
SQL: SELECT i.first_name, i.last_name, COUNT(l.lesson_id) AS lessons
FROM instructor i LEFT JOIN lesson l ON l.instructor_id = i.instructor_id
GROUP BY i.instructor_id ORDER BY lessons DESC;
"""

CROSS_DOMAIN_EXAMPLE = """\
CREATE TABLE author (author_id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE book (book_id INTEGER PRIMARY KEY, title TEXT, author_id INTEGER REFERENCES author(author_id), year INTEGER);
CREATE TABLE loan (loan_id INTEGER PRIMARY KEY, book_id INTEGER REFERENCES book(book_id), loan_date TEXT);

Question: Which author's books have been borrowed the most?
SQL: SELECT a.name, COUNT(*) AS loans
FROM loan l JOIN book b ON b.book_id = l.book_id JOIN author a ON a.author_id = b.author_id
GROUP BY a.author_id ORDER BY loans DESC LIMIT 1;
"""

INSTRUCTIONS = ("You write SQLite queries. Reply with ONE valid SQLite SELECT statement and nothing else "
                "(no explanation, no markdown).")


def sql_prompt(question, strategy):
    if strategy == "zero_shot":
        return f"{SCHEMA}\n\nQuestion: {question}\nSQL:"
    if strategy == "single_domain":
        return f"{SCHEMA}\n\n{SINGLE_DOMAIN_EXAMPLES}\nQuestion: {question}\nSQL:"
    if strategy == "cross_domain":
        return (f"Here is an example from a different database:\n\n{CROSS_DOMAIN_EXAMPLE}\n"
                f"Now answer for this database:\n\n{SCHEMA}\n\nQuestion: {question}\nSQL:")
    raise ValueError(strategy)


# ---------- GPT calls ----------

client = None
usage = {"in": 0, "out": 0}


def chat(system, user):
    global client
    client = client or OpenAI()  # reads OPENAI_API_KEY from the environment
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    usage["in"] += resp.usage.prompt_tokens
    usage["out"] += resp.usage.completion_tokens
    return resp.choices[0].message.content.strip()


def clean_sql(text):
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip()


def ask(question, strategy="single_domain"):
    sql = clean_sql(chat(INSTRUCTIONS, sql_prompt(question, strategy)))
    try:
        cols, rows = run_sql(sql)
        result = f"Columns: {cols}\nRows: {rows[:50]}"
        error = None
    except Exception as e:
        cols, rows, error = [], [], str(e)
        result = f"The query failed with error: {e}"
    answer = chat(
        "You answer questions about a ski resort using query results. Be brief and friendly. "
        "If the results are empty or an error occurred, say you couldn't find the answer.",
        f"Question: {question}\nSQL used: {sql}\n{result}",
    )
    return {"question": question, "strategy": strategy, "sql": sql,
            "rows": rows, "error": error, "answer": answer}


# ---------- auto-checking (execution accuracy) ----------

def norm(v):
    if isinstance(v, float):
        v = int(v) if v.is_integer() else round(v, 2)
    return str(v).strip().lower()


def tokens(row):
    return set(re.findall(r"[\w.]+", " ".join(norm(v) for v in row)))


def matches(rows, gold):
    """True if GPT's rows contain the correct answer: same row count, and every value of each
    correct row shows up in some returned row. Extra columns and different ordering are fine."""
    if not gold:  # correct answer is "none"; also accept a COUNT that says 0
        return not rows or [tuple(map(norm, r)) for r in rows] == [("0",)]
    if len(rows) != len(gold):
        return False
    got = [tokens(r) for r in rows]
    return all(any(tokens(g) <= t for t in got) for g in gold)


def cost():
    pin, pout = PRICES.get(MODEL, (0, 0))
    dollars = usage["in"] / 1e6 * pin + usage["out"] / 1e6 * pout
    return f"{usage['in']} input + {usage['out']} output tokens on {MODEL} ≈ ${dollars:.4f}"


# ---------- modes ----------

def interactive(strategy):
    print(f"Ski resort Q&A ({strategy}, {MODEL}). Ask a question, or 'quit'.\n")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("quit", "exit", "q"):
            break
        if not q:
            continue
        r = ask(q, strategy)
        print(f"\nSQL: {r['sql']}")
        if r["error"]:
            print(f"Error: {r['error']}")
        print(f"Answer: {r['answer']}\n")
    print(cost())


def evaluate():
    lines = [l.strip() for l in (HERE / "questions.txt").read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    questions = [tuple(p.strip() for p in (l.split("||", 1) + [""])[:2]) for l in lines]
    strategies = ["zero_shot", "single_domain", "cross_domain"]
    score = {s: 0 for s in strategies}
    graded = sum(1 for _, gold in questions if gold)
    body = []
    for i, (q, gold_sql) in enumerate(questions, 1):
        body.append(f"## {i}. {q}\n")
        gold = run_sql(gold_sql)[1] if gold_sql else None
        if gold_sql:
            body.append(f"Expected rows: `{gold[:10]}`\n")
        else:
            body.append("_No answer key (subjective or open-ended) — judge by hand._\n")
        for s in strategies:
            print(f"[{i}/{len(questions)}] {s}: {q}")
            r = ask(q, s)
            if gold is None:
                mark = "☐ (check by hand)"
            elif not r["error"] and matches(r["rows"], gold):
                mark, score[s] = "✅", score[s] + 1
            else:
                mark = "❌"
            body.append(f"**{s}** — {mark}\n\n```sql\n{r['sql']}\n```\n")
            if r["error"]:
                body.append(f"SQL error: `{r['error']}`\n")
            body.append(f"> {r['answer']}\n")
    summary = ["| Strategy | Auto-checked correct |", "|---|---|"]
    summary += [f"| {s} | {score[s]}/{graded} |" for s in strategies]
    md = [f"# Results ({MODEL})\n",
          "Every question was run with all three prompting strategies. ✅/❌ means GPT's query returned "
          "the same rows as the hand-written answer key in `questions.txt`; ☐ means there's no key. "
          "Skim the ❌s yourself — some may be reasonable readings of a vague question.\n",
          "\n".join(summary) + "\n", *body, f"\n---\nTotal usage: {cost()}\n"]
    (HERE / "results.md").write_text("\n".join(md), encoding="utf-8")
    print("\n" + "\n".join(summary))
    print(f"\nWrote results.md. {cost()}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", default="single_domain",
                   choices=["zero_shot", "single_domain", "cross_domain"])
    p.add_argument("--eval", action="store_true", help="run questions.txt with all strategies")
    p.add_argument("--rebuild", action="store_true", help="recreate ski.db from schema.sql + data.sql")
    a = p.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY first (never commit it to GitHub).")
    build_db(a.rebuild)
    evaluate() if a.eval else interactive(a.strategy)
