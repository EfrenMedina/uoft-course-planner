# UofT Course Planner

[![CI](https://github.com/EfrenMedina/uoft-course-planner/actions/workflows/ci.yml/badge.svg)](https://github.com/EfrenMedina/uoft-course-planner/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

A desktop app that plans a route through the University of Toronto's prerequisite rules. Tell it which
courses you have finished and which course you want to take. It then shows, step by step, which courses
you can take right now to make progress toward that goal, using the real AND/OR prerequisite logic from
the 2025–26 Arts & Science calendar (**5,349 courses**, about 3,500 of them with prerequisites).

<!-- Add a screenshot of the navigator here, e.g. docs/screenshot.png -->

## Features

- **Prerequisite logic, not just edges.** Each course carries a recursive AND/OR tree, so
  `CSC148H1 AND (CSC165H1 OR CSC240H1)` is kept distinct from `(CSC148H1 AND CSC165H1) OR CSC240H1`.
  Credit thresholds such as "1.0 MAT credit" or "4.0 credits" are supported as tree nodes too.
- **Next-step recommendations.** Given a target and the courses you have done, the planner returns only the
  courses you are eligible for *now* that move you toward the target.
- **Interactive navigator.** A Tkinter GUI with live search, course cards grouped by department, a course
  info panel with a readable prerequisite tree and a link to the calendar, plus undo and start over.
- **Path visualization.** Draws the path you have built as a layered prerequisite graph with Plotly and NetworkX.

## How it works

```mermaid
flowchart LR
    A[A&S calendar HTML] -->|scripts/scrape_calendar.py<br/>BeautifulSoup| B[raw course records<br/>prerequisites as text]
    B -->|structured into<br/>AND/OR trees| C[data/courses.json]
    C -->|json_to_graph.py| D[CourseGraph<br/>vertices + BooleanList trees]
    D --> E[algorithms.py<br/>get_next_needed_courses]
    E --> F[Tkinter navigator]
    F --> G[Plotly path graph]
```

**Data model.** `CourseGraph` stores one vertex per course. Each vertex's prerequisites are a
`BooleanList`, a recursive tree whose children are course codes, nested `BooleanList`s or `CreditCondition`s.
A student's progress is just a set of completed course codes, passed into queries instead of stored in the
graph, so a single graph can serve any student.

**Choosing the next course.** `get_next_needed_courses` walks the target's prerequisite tree recursively:

- **AND nodes** collect suggestions from *every* unsatisfied child, since all of them are needed.
- **OR nodes** pick a branch carefully. If you have already made progress on a branch, the planner keeps
  you on it. If some branch has a course you can take now, it suggests only those ("easy path first").
  Otherwise it recurses into the blocked alternatives.
- A shared `visited` set protects against prerequisite cycles in the calendar data.

[`docs/planner-algorithm.md`](docs/planner-algorithm.md) describes each helper in detail.

## Getting started

Requires Python 3.10+ with Tkinter. Tkinter comes with the python.org installers; on Homebrew Python, run
`brew install python-tk`.

```bash
git clone https://github.com/EfrenMedina/uoft-course-planner.git
cd uoft-course-planner
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Add the courses you have completed, choose a target course, then click **Start navigating**. Click any
suggested course to "take" it and get the next set of options, until you reach the target.

### Using the planner from Python

```python
from course_planner.json_to_graph import load_graph_from_json
from course_planner.algorithms import get_next_needed_courses

graph = load_graph_from_json('data/courses.json')
get_next_needed_courses(graph, 'CSC373H1', {'CSC110Y1', 'CSC111H1', 'MAT137Y1'})
# -> {'CSC236H1', 'CSC240H1', 'STA237H1', 'STA247H1', 'STA257H1'}
```

## Development

```bash
pip install -r requirements-dev.txt
pytest          # unit tests, dataset integration tests, and module doctests
ruff check .
```

The integration tests load the full dataset and simulate a student who keeps taking suggested courses.
They check that targets like `CSC373H1`, `CSC413H1` and `MAT347Y1` are always reached without a dead end.

## Project structure

```
course_planner/
  boolean_list.py     BooleanList (AND/OR tree) and CreditCondition
  course_graph.py     CourseGraph and course vertices
  algorithms.py       prerequisite resolution, relevance filtering, search
  json_to_graph.py    loads data/courses.json into a CourseGraph
  visualizations.py   Plotly/NetworkX layered graph drawing
  interface.py        Tkinter navigator
scripts/
  scrape_calendar.py  calendar HTML -> raw course JSON
data/courses.json     processed dataset (5,349 courses)
docs/                 algorithm notes and the original project report
tests/                pytest suite
```

## Data notes

The course data comes from the University of Toronto Faculty of Arts & Science 2025–26 Academic Calendar.
`scripts/scrape_calendar.py` extracts each course's code, title, description, hours, breadth category,
prerequisite text and exclusions. The free-text prerequisites were then turned into structured AND/OR trees.
The complex cases (deep nesting, mixed conjunctions, credit thresholds) were structured with help from large
language models, with instructor approval. Corequisites appear in the same calendar field as prerequisites,
so they are treated as prerequisites. The data may not reflect calendar changes after 2025–26.

## Background and team

This started as Project 2 for CSC111 (Foundations of Computer Science II) at the University of Toronto in
Winter 2026. It was built by **Jack Anderson**, **Efren Medina Arias**, **Diego Figarella** and
**Tanish Ariyur**. The original repository is [jaandersonck/uoft-course-planner](https://github.com/jaandersonck/uoft-course-planner),
and the original write-up is in [`docs/report.pdf`](docs/report.pdf).
