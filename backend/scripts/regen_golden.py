"""Перегенерация золотого эталона tests/fixtures/schedule/golden.json.

ЗАПУСК ЭТОГО СКРИПТА — ОСОЗНАННОЕ РЕШЕНИЕ, а не шаг починки красного теста.

Эталон — внешний факт о корпусе: «вот пары, которые импорт обязан дать из
этих 23 файлов». Тест test_corpus_matches_golden_reference краснеет в двух
случаях: (1) вы сломали импортёр/парсер — тогда чинить код, а НЕ эталон;
(2) вы осознанно изменили правила разбора и проверили дифф глазами — только
тогда перегенерировать. Запуск по случаю (1) превращает главный сторож
корпуса в тавтологию: он начнёт утверждать «импорт даёт то, что даёт импорт».

Перед перегенерацией посмотрите дифф красного теста и убедитесь, что КАЖДАЯ
изменившаяся строка изменилась по вашему замыслу.

    cd backend && source venv/bin/activate && python scripts/regen_golden.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

import goldens  # noqa: E402
from sqlalchemy import select  # noqa: E402
from test_importer import (  # noqa: E402
    MANIFEST,
    NOT_EXTRACTED_DOC_TYPES,
    FakeFetcher,
    make_session,
)

from src.models import ScheduleDocument  # noqa: E402
from src.schedule import importer  # noqa: E402


def main() -> None:
    session = make_session()
    report = importer.import_all(session, FakeFetcher())
    failed = [d.p_doc_id for d in report.documents if d.error]
    if failed:
        raise SystemExit(f"импорт упал на {failed} — эталон с ошибок не снимают")

    golden: dict[str, dict] = {}
    by_id = {d.p_doc_id: d for d in report.documents}
    for item in MANIFEST:
        p_doc_id = item["id"]
        if by_id[p_doc_id].doc_type in NOT_EXTRACTED_DOC_TYPES:
            continue
        document = session.scalar(
            select(ScheduleDocument).where(ScheduleDocument.p_doc_id == int(p_doc_id))
        )
        golden[p_doc_id] = goldens.document_golden(session, document)

    goldens.GOLDEN_PATH.write_text(
        json.dumps(golden, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    total = sum(doc["lessons"] for doc in golden.values())
    print(
        f"эталон переписан: {len(golden)} документов, {total} пар, "
        f"{sum(d['exams'] for d in golden.values())} экзаменов, "
        f"{sum(d['unparsed'] for d in golden.values())} unparsed → "
        f"{goldens.GOLDEN_PATH}"
    )
    session.close()


if __name__ == "__main__":
    main()
