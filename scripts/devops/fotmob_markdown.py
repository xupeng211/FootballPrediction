"""安装并运行 FotMob 文档门禁的锁定 Markdown 解析器。

lifecycle: permanent
owner: engineering workflow governance
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
import unicodedata

if TYPE_CHECKING:
    from markdown_it.token import Token

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).with_name("fotmob_markdown_requirements.txt")
PARSER_UNAVAILABLE = "FOTMOB_MARKDOWN_PARSER_UNAVAILABLE"
_INVALID_MARKDOWN_EXIT = 2
_HTML_VOID = frozenset(
    (
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    )
)
_HTML_HIDDEN = frozenset(("script", "style", "template"))


def _locked_target() -> Path:
    return ROOT / ".venv" / "fotmob-markdown" / sha256(LOCK.read_bytes()).hexdigest()


def _install_if_requested(target: Path) -> None:
    if target.is_dir():
        return
    if os.environ.get("FP_FOTMOB_MARKDOWN_INSTALL") != "1":
        raise RuntimeError(f"{PARSER_UNAVAILABLE}: use make agent-preflight to install the lock")
    target.parent.mkdir(parents=True, exist_ok=True)
    wheelhouse = os.environ.get("FP_FOTMOB_MARKDOWN_WHEELHOUSE")
    source = (
        ["--no-index", "--find-links", str(Path(wheelhouse).resolve())]
        if wheelhouse
        else ["--index-url", "https://pypi.org/simple"]
    )
    with TemporaryDirectory(dir=target.parent, prefix="install-") as staging:
        package_dir = Path(staging) / "site"
        installed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-m",
                "pip",
                "--isolated",
                "--disable-pip-version-check",
                "--no-input",
                "install",
                "--only-binary",
                ":all:",
                "--require-hashes",
                "--no-deps",
                "--no-compile",
                "--target",
                str(package_dir),
                "--requirement",
                str(LOCK),
                *source,
            ],
            env={**os.environ, "PIP_CONFIG_FILE": os.devnull},
            capture_output=True,
            timeout=90,
            check=False,
        )
        if installed.returncode:
            raise RuntimeError(
                f"{PARSER_UNAVAILABLE}: locked wheel install exited {installed.returncode}; "
                "check host python3 -m pip and the configured wheel source"
            )
        try:
            package_dir.rename(target)
        except OSError:
            if not target.is_dir():
                raise


def visible_documents(*documents: str) -> list[tuple[str, Counter[str]]]:
    """只在 FotMob 门禁需要时使用专用依赖，同一进程解析全部文档。"""
    try:
        _install_if_requested(_locked_target())
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve())],
            input=json.dumps(documents, ensure_ascii=False).encode(),
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"{PARSER_UNAVAILABLE}: {type(exc).__name__}") from exc
    if result.returncode == _INVALID_MARKDOWN_EXIT:
        raise ValueError("invalid authoritative Markdown")
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"{PARSER_UNAVAILABLE}: parser exited {result.returncode}: {detail}")
    try:
        output = json.loads(result.stdout)
        parsed = [(body, Counter(tags)) for body, tags in output]
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{PARSER_UNAVAILABLE}: invalid parser output") from exc
    if len(parsed) != len(documents):
        raise RuntimeError(f"{PARSER_UNAVAILABLE}: document count mismatch")
    return parsed


class _VisibleHtml(HTMLParser):
    """在 Markdown 原始 HTML token 内处理既有的显式隐藏规则。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.tags: Counter[str] = Counter()
        self.heading = False
        self._hidden: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br" and not attrs:
            self.handle_data(" ")
            return
        self.tags[self.get_starttag_text() or tag] += 1
        if tag not in _HTML_VOID and (
            self._hidden or tag in _HTML_HIDDEN or any(name == "hidden" for name, _ in attrs)
        ):
            self._hidden.append(tag)

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag: str) -> None:
        self.tags[f"</{tag}>"] += 1
        if tag in self._hidden:
            while self._hidden.pop() != tag:
                pass

    def handle_decl(self, decl: str) -> None:
        self.tags[f"<!{decl}>"] += 1

    def handle_pi(self, data: str) -> None:
        self.tags[f"<?{data}>"] += 1

    def handle_data(self, data: str) -> None:
        if not self._hidden and not self.heading:
            self.text.append(data)

    def raw_html(self, text: str) -> None:
        if "<!--" in re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL):
            raise ValueError("unterminated HTML comment")
        self.feed(text)


def _project_inline(visible: _VisibleHtml, children: list[Token]) -> None:
    for child in children:
        if child.type == "html_inline":
            visible.raw_html(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            visible.feed(" ")
        elif child.type in {"text", "code_inline"}:
            visible.feed(escape(child.content, quote=False))


def _project(tokens: list[Token]) -> tuple[str, Counter[str]]:
    visible = _VisibleHtml()
    for token in tokens:
        if token.type == "heading_open":
            visible.heading = True
        elif token.type == "heading_close":
            visible.heading = False
        elif token.type == "html_block":
            visible.raw_html(token.content)
        elif token.type in {"fence", "code_block"}:
            visible.feed(escape(token.content, quote=False))
        elif token.type == "inline":
            _project_inline(visible, token.children or [])
        visible.feed(" ")
    visible.close()
    # 保留既有可见字符规则。U+034F 属于 Mn，其余 Mn 字形继续保留。
    clean = "".join(
        char
        for char in "".join(visible.text)
        if char != "\u034f" and unicodedata.category(char) != "Cf"
    )
    normalized = unicodedata.normalize("NFC", clean)
    body = " ".join(normalized.split()) if re.search(r"[^\W_]", normalized) else ""
    return body, visible.tags


def _parse() -> None:
    target = _locked_target()
    expected = dict(
        line.split(" ", 1)[0].split("==")
        for line in LOCK.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )
    installed = {
        dist.metadata["Name"].lower(): dist.version for dist in distributions(path=[target])
    }
    if installed != expected:
        raise RuntimeError(f"{PARSER_UNAVAILABLE}: installed versions differ from the lock")
    sys.path.insert(0, str(target))
    import markdown_it  # noqa: PLC0415
    from markdown_it import MarkdownIt  # noqa: PLC0415
    import mdurl  # noqa: PLC0415

    if any(
        not Path(module.__file__).resolve().is_relative_to(target.resolve())
        for module in (markdown_it, mdurl)
    ):
        raise RuntimeError(f"{PARSER_UNAVAILABLE}: module origin differs from the locked directory")

    parser = MarkdownIt("default", {"html": True})
    documents = json.load(sys.stdin)
    print(json.dumps([_project(parser.parse(text.lstrip("\ufeff"))) for text in documents]))


if __name__ == "__main__":
    try:
        _parse()
    except (AssertionError, ValueError):
        sys.exit(_INVALID_MARKDOWN_EXIT)
    except (ImportError, OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
