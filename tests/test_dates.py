from datetime import date

from processor.dates import format_sheet_date, next_saturday


def test_next_saturday_from_friday():
    assert next_saturday(date(2026, 9, 18)) == date(2026, 9, 19)


def test_next_saturday_keeps_saturday():
    assert next_saturday(date(2026, 9, 19)) == date(2026, 9, 19)


def test_next_saturday_from_sunday():
    assert next_saturday(date(2026, 9, 20)) == date(2026, 9, 26)


def test_sheet_date_format():
    assert format_sheet_date(date(2026, 9, 19)) == "19 / 09 / 2026"
