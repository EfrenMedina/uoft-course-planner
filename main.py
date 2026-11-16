"""Launch the Course Pathway Navigator.

Usage:
    python main.py                       # use the bundled course dataset
    python main.py path/to/courses.json  # use a different dataset
"""
import sys

from course_planner.interface import run

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        run()
