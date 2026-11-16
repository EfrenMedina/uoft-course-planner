"""Pytest configuration shared by the test suite and the module doctests."""
# The Tk interface opens a window on import of tkinter widgets and needs a display,
# so it is excluded from doctest collection.
collect_ignore = ['course_planner/interface.py']
