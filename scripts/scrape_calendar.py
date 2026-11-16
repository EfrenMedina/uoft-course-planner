"""Scrape course records from a saved copy of the UofT Arts & Science calendar.

This is step 1 of the data pipeline. It reads the calendar's course listing HTML
and writes one JSON record per course, keeping the prerequisite as raw text:

    python scripts/scrape_calendar.py data/raw/courses.html data/raw/courses.json

Step 2 (converting each prerequisite sentence into the nested AND/OR
``prereq_tree`` used in data/courses.json) was done separately; see the README.
"""
from __future__ import annotations

import argparse
import json

from bs4 import BeautifulSoup
from bs4.element import Tag


def _field_text(row: Tag, field_class: str) -> str | None:
    """Return the stripped text of the given calendar field in row, or None if absent."""
    field = row.find(class_=field_class)
    if field is None:
        return None
    content = field.find(class_='field-content')
    return content.get_text().strip() if content else None


def parse_course(row: Tag) -> dict:
    """Return a course record parsed from a single calendar listing row."""
    title_parts = _field_text(row, 'views-field-title').split(' ')
    breadth_text = _field_text(row, 'views-field-field-breadth-requirements')
    breadth = None
    if breadth_text:
        breadth = int(breadth_text.split(' ')[-1].strip('()'))

    return {
        'code': title_parts[0],
        'name': ' '.join(title_parts[2:]),
        'hours': _field_text(row, 'views-field-field-hours'),
        'description': _field_text(row, 'views-field-body'),
        'prerequisites': _field_text(row, 'views-field-field-prerequisite'),
        'exclusions': _field_text(row, 'views-field-field-exclusion'),
        'breadth': breadth,
    }


def scrape(html_path: str) -> dict[str, dict]:
    """Return a mapping from course code to course record for every course in html_path."""
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    courses = {}
    for row in soup.find(class_='view-content'):
        if isinstance(row, Tag):
            course = parse_course(row)
            courses[course['code']] = course
    return courses


def main() -> None:
    """Parse command-line arguments and write the scraped courses to JSON."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('html', help='saved calendar HTML page')
    parser.add_argument('output', help='path of the JSON file to write')
    args = parser.parse_args()

    courses = scrape(args.html)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2)
    print(f'Wrote {len(courses)} courses to {args.output}')


if __name__ == '__main__':
    main()
