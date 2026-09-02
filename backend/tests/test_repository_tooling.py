import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
README = BACKEND / "README.md"
PROJECT_README = ROOT / "README.md"
SCREENSHOTS = {
    "assets/readme/01-schedule.png",
    "assets/readme/02-news.png",
    "assets/readme/03-contacts.png",
    "assets/readme/04-assistant.png",
}
SCREENSHOT_CAPTIONS = {
    "assets/readme/01-schedule.png": "Расписание",
    "assets/readme/02-news.png": "Новости",
    "assets/readme/03-contacts.png": "Контакты",
    "assets/readme/04-assistant.png": "AI-помощник",
}


class _HTMLTargetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.targets.append(value)


def _relative_targets(markdown: str) -> set[str]:
    markdown_targets = [
        match.group("angle") or match.group("plain")
        for match in re.finditer(
            r"!?\[[^\]]*\]\(\s*(?:<(?P<angle>[^>]+)>|(?P<plain>[^)\s]+))",
            markdown,
        )
    ]
    html_parser = _HTMLTargetParser()
    html_parser.feed(markdown)

    targets: set[str] = set()
    for raw in [*markdown_targets, *html_parser.targets]:
        target = unquote(raw.strip().strip("<>"))
        if not target or target.startswith("#"):
            continue
        parsed = urlsplit(target)
        if parsed.scheme.lower() in {"http", "https", "mailto"}:
            continue
        if parsed.netloc or parsed.path.startswith("/"):
            continue
        if parsed.path:
            targets.add(parsed.path)
    return targets


def _markdown_section(markdown: str, heading: str) -> str:
    heading_match = re.search(rf"(?m)^{re.escape(heading)}\s*$", markdown)
    assert heading_match is not None
    following = markdown[heading_match.end() :]
    next_heading = re.search(r"(?m)^## ", following)
    end = heading_match.end() + (
        next_heading.start() if next_heading else len(following)
    )
    return markdown[heading_match.start() : end]


def _requirement_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-r")):
            continue
        names.add(re.split(r"[<>=!~\[]", line, maxsplit=1)[0].lower())
    return names


def _workflow_job(text: str, name: str) -> str:
    jobs = re.search(r"(?m)^jobs:\s*$", text)
    assert jobs is not None
    jobs_text = text[jobs.end() :]
    job = re.search(rf"(?m)^  {re.escape(name)}:\s*$", jobs_text)
    assert job is not None
    following = jobs_text[job.end() :]
    next_job = re.search(r"(?m)^  [A-Za-z0-9_-]+:\s*$", following)
    end = job.end() + next_job.start() if next_job else len(jobs_text)
    return jobs_text[job.start() : end]


def _workflow_step(job: str, name: str) -> str:
    step = re.search(
        rf"(?m)^(?P<indent> +)- name: {re.escape(name)}\s*$",
        job,
    )
    assert step is not None
    following = job[step.end() :]
    step_prefix = " " * len(step.group("indent")) + "- "
    next_step = re.search(rf"(?m)^{re.escape(step_prefix)}", following)
    end = step.end() + next_step.start() if next_step else len(job)
    return job[step.start() : end]


def _yaml_value_lines(block: str, key: str) -> list[str]:
    match = re.search(
        rf"(?m)^(?P<indent> +){re.escape(key)}:\s*(?P<value>[^\n]*)$", block
    )
    assert match is not None
    value = match.group("value").strip()
    if value not in {"", "|", "|-", "|+", ">", ">-", ">+"}:
        return [value.strip("'\"")]

    key_indent = len(match.group("indent"))
    values: list[str] = []
    for raw_line in block[match.end() :].splitlines():
        if not raw_line.strip():
            continue
        indentation = len(raw_line) - len(raw_line.lstrip())
        if indentation <= key_indent:
            break
        values.append(raw_line.strip().strip("'\""))
    return values


def test_runtime_requirements_exclude_development_tools() -> None:
    runtime = _requirement_names(BACKEND / "requirements.txt")
    assert runtime.isdisjoint({"pytest", "ruff"})
    assert "httpx" in runtime


def test_development_requirements_extend_runtime() -> None:
    lines = (BACKEND / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()
    development = _requirement_names(BACKEND / "requirements-dev.txt")
    assert "-r requirements.txt" in lines
    assert {"pytest", "ruff"} <= development
    assert "ruff==0.16.5" in lines
    assert lines.count("PyYAML==6.0.3") == 1
    assert "httpx" not in development


def test_backend_ci_installs_development_requirements() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    backend_job = _workflow_job(workflow, "backend")
    assert "pip install -r requirements-dev.txt" in backend_job


def test_backend_ci_cache_tracks_development_requirements() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    backend_job = _workflow_job(workflow, "backend")
    cache_paths = set(_yaml_value_lines(backend_job, "cache-dependency-path"))
    assert {"backend/requirements.txt", "backend/requirements-dev.txt"} <= cache_paths


def test_flutter_ci_formats_every_tracked_manual_dart_file() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    flutter_job = _workflow_job(workflow, "flutter")
    format_step = _workflow_step(flutter_job, "Check Dart formatting")
    command = " ".join(_yaml_value_lines(format_step, "run"))

    tracked_dart_command = "git ls-files -z -- '*.dart' ':!**/db.g.dart'"
    assert tracked_dart_command in command
    assert "find lib test" not in command
    assert _yaml_value_lines(format_step, "shell") == ["bash"]
    assert "set -o pipefail" in command
    assert "xargs -0 dart format" in command
    assert "--output=none" in command
    assert "--set-exit-if-changed" in command


def test_local_development_installs_test_requirements() -> None:
    readme = README.read_text(encoding="utf-8")
    development_start = readme.index("## Разработка локально")
    tests_start = readme.index("## Тесты", development_start)
    development = readme[development_start:tests_start]
    install_command = "pip install -r requirements-dev.txt"
    assert install_command in development
    assert readme.index(install_command, development_start) < readme.index(
        "pytest", tests_start
    )


def test_readme_target_parser_handles_markdown_and_html() -> None:
    markdown = """
    [Backend](backend/README.md?view=1#api)
    ![Schedule](assets/readme/01%2Dschedule.png#full)
    <a href="app/README.md#launch">App</a>
    <img src="assets/readme/02-news.png?raw=1" alt="News">
    [Web](https://example.com/readme)
    <a href="http://example.com">HTTP</a>
    <a href="mailto:author@example.com">Email</a>
    <a href="#section">Section</a>
    """

    assert _relative_targets(markdown) == {
        "app/README.md",
        "assets/readme/01-schedule.png",
        "assets/readme/02-news.png",
        "backend/README.md",
    }


def test_readme_centered_subtitle_describes_the_mobile_product() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    match = re.search(
        r'<p align="center">\s*<strong>(?P<subtitle>.*?)</strong>',
        text,
        re.DOTALL,
    )
    assert match is not None
    subtitle = " ".join(match.group("subtitle").casefold().split())
    required_phrases = {
        "неофициальное мобильное приложение",
        "расписание",
        "экзамены",
        "новости",
        "контакты",
        "ai-помощник",
    }

    missing = sorted(phrase for phrase in required_phrases if phrase not in subtitle)
    assert missing == []


def test_readme_centered_badges_cover_release_stack_and_license() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    centered_blocks = re.findall(
        r'<p align="center">(?P<content>.*?)</p>', text, re.DOTALL
    )
    badge_block = next((block for block in centered_blocks if "<img" in block), "")
    assert badge_block
    required_badges = {
        "actions/workflows/ci.yml",
        "actions/workflows/security.yml",
        "actions/workflows/android-beta.yml",
        "badge/Flutter-3.44",
        "badge/Python-3.12",
        "badge/license-AGPL--3.0",
    }

    missing = sorted(badge for badge in required_badges if badge not in badge_block)
    assert missing == []


def test_readme_showcase_screenshots_are_clickable_and_compact() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    showcase_targets = {
        target
        for target in _relative_targets(text)
        if target.startswith("assets/readme/")
    }

    assert showcase_targets == SCREENSHOTS
    showcase = _markdown_section(text, "## Как выглядит приложение")
    table_match = re.search(r"<table>(?P<table>.*?)</table>", showcase, re.DOTALL)
    assert table_match is not None
    rows = re.findall(r"<tr>(?P<row>.*?)</tr>", table_match.group("table"), re.DOTALL)
    assert len(rows) == 1
    cells = re.findall(r"<td\b[^>]*>(?P<cell>.*?)</td>", rows[0], re.DOTALL)
    assert len(cells) == 4

    for screenshot, caption in SCREENSHOT_CAPTIONS.items():
        assert text.count(screenshot) == 2
        cell = next(
            (cell for cell in cells if f"<strong>{caption}</strong>" in cell), ""
        )
        assert cell
        image = re.search(
            rf'<a href="{re.escape(screenshot)}">\s*'
            rf'<img src="{re.escape(screenshot)}"(?P<attrs>[^>]*)>\s*</a>',
            cell,
            re.DOTALL,
        )
        assert image is not None
        width = re.search(r'\bwidth="(?P<width>\d+)"', image.group("attrs"))
        assert width is not None
        assert 200 <= int(width.group("width")) <= 240
        assert re.search(r'\balt="[^"]+"', image.group("attrs")) is not None


def test_readme_capabilities_cover_semesters_and_the_unified_directory() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    capabilities = " ".join(
        _markdown_section(text, "## Возможности").casefold().split()
    )

    assert "выбор семестра" in capabilities
    assert "единый справочник преподавателей и деканата" in capabilities


def test_readme_beta_section_explains_safe_installation_and_updates() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    beta = " ".join(_markdown_section(text, "## Получить beta APK").casefold().split())

    assert "не устанавливайте apk из сторонних источников" in beta
    assert re.search(r"обновлени[ея].*подписанн\w+ тем же ключом", beta) is not None
    assert re.search(r"(?:ставится|устанавливается) поверх", beta) is not None
    assert "сохраняет локальные данные" in beta
    assert re.search(r"app store|google play|play store", text, re.IGNORECASE) is None


def test_readme_documents_reproducible_backend_checks() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    checks = _markdown_section(text, "## Проверки и безопасность")
    commands = (
        "pip install -r requirements-dev.txt",
        "ruff check .",
        "ruff format --check .",
        "pytest -q",
    )

    positions: list[int] = []
    for command in commands:
        assert command in checks
        positions.append(checks.index(command))
    assert positions == sorted(positions)


def test_readme_documents_reproducible_flutter_checks() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    checks = _markdown_section(text, "## Проверки и безопасность")
    commands = (
        "flutter pub get",
        "git ls-files -z -- '*.dart' ':!**/db.g.dart'",
        "xargs -0 dart format --output=none --set-exit-if-changed",
        "flutter analyze",
        "flutter test",
    )

    positions: list[int] = []
    for command in commands:
        assert command in checks
        positions.append(checks.index(command))
    assert positions == sorted(positions)
    assert "find lib test" not in checks


def test_readme_explains_golden_and_migration_check_limitations() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    checks = " ".join(
        _markdown_section(text, "## Проверки и безопасность").casefold().split()
    )

    assert "golden" in checks
    assert "docx" in checks
    assert "pdf" in checks
    assert "alembic upgrade head" in checks
    assert "alembic check" in checks
    assert (
        "не гарантируют абсолютную актуальность данных и отсутствие всех ошибок"
        in checks
    )


def test_readme_has_public_sections_and_contact() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    assert '<h1 align="center">Эконом ЮФУ</h1>' in text
    assert text.count('<p align="center">') >= 2
    assert "**Неофициальный проект.**" in text
    assert "## Получить beta APK" in text
    assert "080806oleg@gmail.com" in text


def test_readme_relative_links_and_images_exist() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    missing = sorted(
        target for target in _relative_targets(text) if not (ROOT / target).exists()
    )
    assert missing == []


def test_readme_does_not_expose_internal_planning_docs() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    assert re.search(r"(?:docs/)?superpowers", text, re.IGNORECASE) is None


def test_readme_author_contact_is_email_only() -> None:
    text = PROJECT_README.read_text(encoding="utf-8")
    author_heading = "## Автор"
    assert author_heading in text
    author = text[text.index(author_heading) :].strip()

    assert author == (
        "## Автор\n\n"
        "**Олег Роговенко**\n\n"
        "[080806oleg@gmail.com](mailto:080806oleg@gmail.com)"
    )
