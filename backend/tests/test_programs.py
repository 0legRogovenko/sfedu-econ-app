"""Канонизация магистерских программ.

Одна и та же программа приходит из двух источников разным написанием: файлы
расписания дают ЧИСТОЕ имя («Корпоративные финансы»), файлы сессий — то же имя
в обёртке «Магистерская программа «…»» с опечатками, переносами и лишними
пробелами. Без канонизации это две РАЗНЫЕ группы: у одной только пары, у другой
только экзамены. canonical_program сводит оба написания к одному из шести
канонических имён — тогда find-or-create по (курс, программа) кладёт пары и
экзамены в одну группу.

Фаззи-матч здесь безопасен именно потому, что множество закрытое (ровно 6
программ) и элементы далеки друг от друга: ложного слияния разных программ не
бывает. Незнакомую строку канонизатор НЕ форсит в чужую программу — возвращает
как есть, чтобы новая программа 2027 года не слилась с существующей по ошибке.
"""

from __future__ import annotations

import pytest

from src.schedule.programs import CANONICAL_PROGRAMS, canonical_program


class TestCleanNamesAreTheirOwnCanonical:
    """Шесть чистых имён из файлов расписания — уже канонические."""

    @pytest.mark.parametrize("name", CANONICAL_PROGRAMS)
    def test_canonical_name_maps_to_itself(self, name):
        assert canonical_program(name) == name


class TestWrapperIsStripped:
    """«Магистерская программа «X»» → «X»: снять обёртку файлов сессий."""

    def test_plain_wrapper(self):
        assert (
            canonical_program("Магистерская программа «Экономическая аналитика»")
            == "Экономическая аналитика"
        )

    def test_wrapper_on_all_six(self):
        for name in CANONICAL_PROGRAMS:
            wrapped = f"Магистерская программа «{name}»"
            assert canonical_program(wrapped) == name


class TestDirtyVariantsFold:
    """Опечатки, лишние пробелы и переносы схлопываются к канону."""

    def test_typo(self):
        # «Корпоративнве» вместо «Корпоративные» — одна подмена буквы
        assert (
            canonical_program("Магистерская программа «Корпоративнве финансы»")
            == "Корпоративные финансы"
        )

    def test_extra_space(self):
        # «Корпоративны е финансы» — вклинившийся пробел
        assert (
            canonical_program("Магистерская программа «Корпоративны е финансы»")
            == "Корпоративные финансы"
        )

    def test_hyphenation(self):
        # «Корпоратив-ные финансы» — перенос строки
        assert (
            canonical_program("Магистерская программа «Корпоратив-ные финансы»")
            == "Корпоративные финансы"
        )


class TestUnknownIsNotForced:
    """Незнакомую программу НЕ сливаем с чужой — возвращаем исходное."""

    def test_unknown_program_returns_itself(self):
        raw = "Магистерская программа «Новая программа 2027»"
        assert canonical_program(raw) == raw

    def test_unrelated_string_returns_itself(self):
        raw = "Совершенно посторонний текст без смысла"
        assert canonical_program(raw) == raw


class TestIdempotency:
    """canonical(canonical(x)) == canonical(x) для любого входа."""

    @pytest.mark.parametrize(
        "raw",
        [
            "Корпоративные финансы",
            "Магистерская программа «Экономическая аналитика»",
            "Магистерская программа «Корпоративнве финансы»",
            "Магистерская программа «Корпоративны е финансы»",
            "Магистерская программа «Корпоратив-ные финансы»",
            "Магистерская программа «Новая программа 2027»",
            "International Economics and Analytics (Международная экономика и аналитика)",
        ],
    )
    def test_double_application_is_stable(self, raw):
        once = canonical_program(raw)
        assert canonical_program(once) == once


class TestDistinctProgramsNeverMerge:
    """Разные канонические программы не сливаются друг с другом.

    Страховка сути «фаззи здесь безопасен»: каждая из шести программ канонична
    сама себе и НЕ уезжает в соседнюю. Если порог однажды задерут так, что две
    программы начнут путаться, этот тест покраснеет.
    """

    def test_each_pair_stays_apart(self):
        for name in CANONICAL_PROGRAMS:
            assert canonical_program(name) == name
