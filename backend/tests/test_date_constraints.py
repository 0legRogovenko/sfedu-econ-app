"""Exact rules for converting a schedule date prefix into visibility data."""

from datetime import date

from src.schedule.date_constraints import ResolvedDates, resolve_date_constraint

AUTUMN = (date(2025, 9, 1), date(2026, 1, 11))
SPRING = (date(2026, 4, 13), date(2026, 6, 22))


def test_no_constraint_keeps_base_window():
    assert resolve_date_constraint(None, *AUTUMN) == ResolvedDates(*AUTUMN)


def test_until_narrows_upper_bound_across_new_year():
    assert resolve_date_constraint("До 17.12", *AUTUMN) == ResolvedDates(
        date(2025, 9, 1), date(2025, 12, 17)
    )


def test_lowercase_po_is_an_upper_bound():
    assert resolve_date_constraint("по 26.05", *SPRING) == ResolvedDates(
        date(2026, 4, 13), date(2026, 5, 26)
    )


def test_since_narrows_lower_bound():
    assert resolve_date_constraint("С 28.04", *SPRING) == ResolvedDates(
        date(2026, 4, 28), date(2026, 6, 22)
    )


def test_since_until_becomes_closed_range():
    assert resolve_date_constraint("С 28.04 по 26.05", *SPRING) == ResolvedDates(
        date(2026, 4, 28), date(2026, 5, 26)
    )


def test_sparse_list_stays_exact_instead_of_becoming_a_span():
    assert resolve_date_constraint("08.11, 15.11", *AUTUMN) == ResolvedDates(
        date(2025, 11, 8),
        date(2025, 11, 15),
        (date(2025, 11, 8), date(2025, 11, 15)),
    )


def test_single_date_is_exact():
    assert resolve_date_constraint("24.12", *AUTUMN) == ResolvedDates(
        date(2025, 12, 24), date(2025, 12, 24), (date(2025, 12, 24),)
    )


def test_exact_dates_outside_base_window_are_discarded():
    assert resolve_date_constraint("09.04, 23.04", *SPRING) == ResolvedDates(
        date(2026, 4, 23), date(2026, 4, 23), (date(2026, 4, 23),)
    )


def test_constraint_without_a_datable_base_is_rejected():
    assert resolve_date_constraint("24.12", None, None) is None


def test_constraint_with_empty_intersection_is_rejected():
    assert resolve_date_constraint("До 01.01", *SPRING) is None
