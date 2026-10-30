#!/usr/bin/env python3
"""BBPlus noncommercial, public-page extraction utility.

No login, cookies, account sessions, private APIs, or access-control bypasses.
Only collects BBPlus-owned/approved content, subject to the user's license.
This is NOT an official or endorsed BBPlus tool.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote

import requests
from bs4 import BeautifulSoup, Tag

HOSTS = {"bbplus.plus", "www.bbplus.plus"}
ROOT = "https://bbplus.plus/"
INDEXES = [
    "https://bbplus.plus/bluebook-plus-digital-sat-tests/",
    "https://bbplus.plus/bluebook-plus-question-bank/",
    "https://bbplus.plus/courses/",
]
QUIZ_PATTERN = re.compile(r"/courses/[^?#]+/quizzes/[^?#]+/?", re.I)
COURSE_PATTERN = re.compile(r"^/courses/[^/]+/?$", re.I)
CONTAINER_SELECTORS = [
    ".wpProQuiz_question",
    "div.wpProQuiz_question",
]
SKIP_TAGS = "script,style,noscript,iframe,button,input,textarea,select"
UI_MARKERS = ".wpProQuiz_response,.wpProQuiz_correct,.wpProQuiz_incorrect,.wpProQuiz_answerCorrect,.wpProQuiz_questionListItem > input"
DOWNLOAD_TIMEOUT = 25
LOG = logging.getLogger("bbplus")


def normalize(url: str, base: str = ROOT) -> str | None:
    absolute = urljoin(base, url.strip())
    p = urlsplit(absolute)
    if p.scheme not in ("https", "http") or (p.hostname or "").lower() not in HOSTS:
        return None
    if not p.path.startswith(("/courses/", "/bluebook-plus-", "/wp-content/uploads/")):
        return None
    return urlunsplit(("https", p.netloc.lower(), p.path or "/", "", ""))


def clean_text(node: Tag | None) -> str:
    if node is None:
        return ""
    copy = BeautifulSoup(str(node), "html.parser")
    for tag in copy.select(SKIP_TAGS + "," + UI_MARKERS):
        tag.decompose()
    return " ".join(copy.stripped_strings)


def clean_html(node: Tag | None) -> str:
    if node is None:
        return ""
    copy = BeautifulSoup(str(node), "html.parser")
    for tag in copy.select(SKIP_TAGS + "," + UI_MARKERS):
        tag.decompose()
    for tag in copy.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                tag.attrs.pop(attr, None)
        for attr in ("src", "href"):
            if tag.has_attr(attr) and str(tag[attr]).strip().lower().startswith("javascript:"):
                del tag.attrs[attr]
    return "".join(str(child) for child in (copy.body or copy).contents)


def choice_info(node: Tag, ix: int) -> dict[str, Any]:
    label = node.select_one("label") or node
    attr_truth = [str(node.get(k, "")).lower() for k in ("data-correct", "data-is-correct")]
    # Most LearnDash quiz pages do not publicly reveal which option is correct.
    # Do not infer an answer from a generic 'Correct answer' status label.
    is_correct: bool | None = True if "true" in attr_truth or "1" in attr_truth else None
    return {
        "index": ix,
        "text": clean_text(label),
        "html": clean_html(label),
        "correct_if_explicitly_marked": is_correct,
    }


def collect_media(block: Tag, base: str) -> list[str]:
    assets = []
    for image in block.select("img"):
        for attr in ("src", "data-src"):
            raw = image.get(attr)
            if raw:
                url = normalize(str(raw), base)
                if url and "/wp-content/uploads/" in url and url not in assets:
                    assets.append(url)
                break
    return assets


def extract_quiz(html: str, url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select(CONTAINER_SELECTORS[0])
    found = []
    for n, box in enumerate(nodes, 1):
        text_node = box.select_one(".wpProQuiz_question_text")
        choice_nodes = box.select(".wpProQuiz_questionListItem")
        if not choice_nodes:
            question_list = box.select_one(".wpProQuiz_questionList")
            if question_list:
                choice_nodes = question_list.find_all("li", recursive=False)
        if text_node is None and not choice_nodes:
            continue
        choices = [choice_info(item, i) for i, item in enumerate(choice_nodes)]
        # Response messages often only contain 'Correct' and 'Incorrect', not explanations.
        explanation_nodes = box.select(".wpProQuiz_response .wpProQuiz_correct, .wpProQuiz_response .wpProQuiz_incorrect")
        explanations = []
        for ex in explanation_nodes:
            value = clean_text(ex)
            if value and value.lower().strip(" .:!") not in {"correct", "incorrect", "correct answer"}:
                if value not in explanations:
                    explanations.append(value)
        # Only record correct answers where the DOM explicitly marks them.
        correct = [c["index"] for c in choices if c["correct_if_explicitly_marked"] is True]
        q_list = box.select_one(".wpProQuiz_questionList")
        content = clean_text(text_node)
        if not content and not choices:
            continue
        found.append({
            "id": hashlib.sha256((url + "#" + str(n)).encode()).hexdigest()[:24],
            "source": "bbplus.plus",
            "source_url": url,
            "number": n,
            "question_id_on_page": q_list.get("data-question_id") if q_list else None,
            "question_type": q_list.get("data-type") if q_list else None,
            "question_text": content,
            "question_html": clean_html(text_node),
            "choices": choices,
            "correct_option_indexes": correct if correct else None,
            "explanations": explanations,
            "media_urls": collect_media(box, url),
            "rights_status": "REVIEW: BBPlus or authorized sublicensed content only",
        })
    return found


def discovered_links(html: str, url: str) -> tuple[set[str], set[str]]:
    soup = BeautifulSoup(html, "html.parser")
    quizzes: set[str] = set()
    courses: set[str] = set()
    for tag in soup.select("a[href]"):
        link = normalize(str(tag.get("href")), url)
        if not link:
            continue
        p = urlsplit(link).path
        if QUIZ_PATTERN.search(p):
            quizzes.add(link)
        elif COURSE_PATTERN.fullmatch(p):
            courses.add(link)
    return quizzes, courses


class Downloader:
    def __init__(self, delay: float = 2.0):
        self.delay = max(delay, 1.0)
        self.last_request = 0.0
        self.total = 0

    def get(self, url: str, *, binary: bool = False) -> tuple[str, bytes | None, str]:
        """No cookie jar, no authentication, no cross-site redirects."""
        current = normalize(url)
        if not current:
            return "not_allowed", None, url
        for _ in range(5):
            remaining = self.delay - (time.monotonic() - self.last_request)
            if remaining > 0:
                time.sleep(remaining)
            self.last_request = time.monotonic()
            self.total += 1
            try:
                response = requests.get(
                    current,
                    headers={
                        "User-Agent": "BBPlusAuthorizedNoncommercialEducationExporter/1.0",
                        "Accept": "text/html,application/xhtml+xml,image/*;q=0.8",
                    },
                    timeout=DOWNLOAD_TIMEOUT,
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                return "network_error:" + type(exc).__name__, None, current
            # Do not read or store Set-Cookie headers or send any cookies.
            if response.status_code in (301, 302, 303, 307, 308):
                nxt = normalize(response.headers.get("Location", ""), current)
                if not nxt:
                    return "redirected_off_domain_or_unapproved_path", None, current
                current = nxt
                continue
            if response.status_code in (401, 403):
                return "login_required_or_forbidden", None, current
            if response.status_code == 429:
                return "rate_limited_STOP", None, current
            if response.status_code >= 400:
                return f"http_{response.status_code}", None, current
            if binary:
                return "ok", response.content, current
            ct = response.headers.get("Content-Type", "")
            if "html" not in ct.lower() and not response.content.lstrip().startswith(b"<"):
                return "not_html", None, current
            return "ok", response.content, current
        return "too_many_redirects", None, current


@dataclass
class PageReport:
    url: str
    final_url: str
    status: str
    questions_found: int = 0
    title: str = ""


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="bbplus_export", help="Destination directory")
    ap.add_argument("--delay", type=float, default=2.0, help="Minimum seconds between requests (>=1)")
    ap.add_argument("--max-pages", type=int, default=500, help="Maximum quiz pages")
    ap.add_argument("--max-courses", type=int, default=80, help="Maximum course pages")
    ap.add_argument("--urls", help="Optional text file of additional approved quiz URLs, one per line")
    ap.add_argument("--no-assets", action="store_true", help="Do not download images")
    ap.add_argument("--urls-only", action="store_true", help="Scan only URLs passed through --urls (no catalog discovery)")
    ap.add_argument("--newest-first", action="store_true", help="Sort dated modules with the most recent years first")
    ap.add_argument("--start-index", type=int, default=0, help="Zero-based starting index in the ordered URL list")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    dl = Downloader(args.delay)
    pending_quizzes: set[str] = set()
    course_urls: set[str] = set()
    reports: list[PageReport] = []
    originals: dict[str, list[dict[str, Any]]] = {}
    status_stop = False

    # Review each selected site's rights before copying content. The license
    # provided in conversation does NOT authorize content belonging to others.
    for start in ([] if args.urls_only else INDEXES):
        LOG.info("Discover %s", start)
        status, data, final = dl.get(start)
        reports.append(PageReport(start, final, status))
        if status == "rate_limited_STOP":
            status_stop = True
            break
        if status != "ok" or not data:
            continue
        qs, cs = discovered_links(data.decode("utf-8", "replace"), final)
        pending_quizzes.update(qs)
        course_urls.update(cs)
        LOG.info("Found %d quiz links, %d course links", len(qs), len(cs))

    # Explore public course listings only, without credentials or private APIs.
    if not status_stop:
        for i, url in enumerate(sorted(course_urls)[:max(args.max_courses, 0)], 1):
            LOG.info("Course %d: %s", i, url)
            status, data, final = dl.get(url)
            reports.append(PageReport(url, final, status))
            if status == "rate_limited_STOP":
                status_stop = True
                break
            if status != "ok" or not data:
                continue
            qs, _ = discovered_links(data.decode("utf-8", "replace"), final)
            pending_quizzes.update(qs)

    if args.urls and not status_stop:
        for row in Path(args.urls).read_text(encoding="utf-8").splitlines():
            candidate = normalize(row)
            if candidate and QUIZ_PATTERN.search(urlsplit(candidate).path):
                pending_quizzes.add(candidate)

    def sort_key(url: str) -> tuple[int, str]:
        match = re.search(r"/courses/(20\d{2})[-/]", url)
        return (-(int(match.group(1)) if match else 0), url)

    ordered = sorted(pending_quizzes, key=sort_key if args.newest_first else None)
    write_json(out / "discovered_quiz_urls.json", ordered)
    LOG.info("Total discovered quiz pages: %s", len(pending_quizzes))
    if args.start_index < 0:
        ap.error("--start-index must be >= 0")
    selected = ordered[args.start_index:args.start_index + max(0, args.max_pages)]
    questions: list[dict[str, Any]] = []
    for i, url in enumerate(selected, 1):
        if status_stop:
            break
        LOG.info("Module %d/%d: %s", i, len(selected), url)
        status, data, final = dl.get(url)
        if status == "rate_limited_STOP":
            status_stop = True
        if status != "ok" or not data:
            reports.append(PageReport(url, final, status))
            continue
        html = data.decode("utf-8", errors="replace")
        parsed = BeautifulSoup(html, "html.parser")
        title = parsed.title.get_text(" ", strip=True) if parsed.title else ""
        found = extract_quiz(html, final)
        report_status = "extracted" if found else "html_no_question_nodes"
        if not found and urlsplit(final).path.rstrip("/") != urlsplit(url).path.rstrip("/"):
            report_status = "redirected_to_different_bbplus_page"
        elif not found and re.search(r"(you don.t currently have access to this content|this practice exam is currently closed|enroll in this practice exam to get access)", parsed.get_text(" ", strip=True), re.I):
            report_status = "course_closed_or_not_enrolled"
        if not found:
            LOG.info("  No questions. final=%s title=%r status=%s", final, title[:90], report_status)
        reports.append(PageReport(url, final, report_status, len(found), title))
        questions.extend(found)
        if found:
            originals[url] = found
        # Save progress every module so interrupts preserve work.
        with (out / "questions.jsonl").open("w", encoding="utf-8") as f:
            for question in questions:
                f.write(json.dumps(question, ensure_ascii=False) + "\n")

    images_saved: dict[str, str] = {}
    if not args.no_assets and not status_stop:
        media = sorted({u for q in questions for u in q["media_urls"]})
        assets_dir = out / "assets"
        assets_dir.mkdir(exist_ok=True)
        for url in media:
            status, content, final = dl.get(url, binary=True)
            if status == "rate_limited_STOP":
                status_stop = True
                break
            if status != "ok" or not content or len(content) > 15 * 1024 * 1024:
                continue
            suffix = Path(unquote(urlsplit(final).path)).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
                suffix = ".bin"
            fname = hashlib.sha256(content).hexdigest()[:20] + suffix
            (assets_dir / fname).write_bytes(content)
            images_saved[url] = "assets/" + fname
    write_json(out / "downloaded_assets.json", images_saved)

    # Compact CSV for inspection; rich HTML/choice structures remain in JSONL.
    with (out / "questions_index.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "source_url", "number", "question_type", "question_text", "choice_count", "verified_answer", "rights_status"])
        writer.writeheader()
        for q in questions:
            writer.writerow({
                "id": q["id"], "source_url": q["source_url"], "number": q["number"],
                "question_type": q["question_type"], "question_text": q["question_text"],
                "choice_count": len(q["choices"]),
                "verified_answer": json.dumps(q["correct_option_indexes"]),
                "rights_status": q["rights_status"],
            })
    status_counts = Counter(r.status for r in reports)
    write_json(out / "extraction_report.json", {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "allowed_domain": "bbplus.plus",
        "license_window_provided_by_user": ["2026-10-29", "2027-04-29"],
        "noncommercial_only": True,
        "not_covered": ["Third-party content without sublicensing rights", "Real Prep Plus content", "Password/account/cookie data"],
        "access_mode": "Unauthenticated public HTML only, no cookies, no login, no private endpoints",
        "discovered_quizzes": len(pending_quizzes),
        "selected_quizzes": len(selected),
        "start_index": args.start_index,
        "newest_first": bool(args.newest_first),
        "urls_only": bool(args.urls_only),
        "scanned_quizzes": len([r for r in reports if QUIZ_PATTERN.search(urlsplit(r.url).path)]),
        "questions_extracted": len(questions),
        "verified_answers_found": sum(q["correct_option_indexes"] is not None for q in questions),
        "images_saved": len(images_saved),
        "stopped_by_429_rate_limit": status_stop,
        "statuses": dict(status_counts),
        "pages": [asdict(r) for r in reports],
    })
    print("\nExport directory:", out)
    print("Discovered module URLs:", len(pending_quizzes))
    print("Extracted questions:", len(questions))
    print("Images saved:", len(images_saved))
    print("Status counts:", dict(status_counts))
    if not questions:
        print("No question content extracted. Review extraction_report.json: pages may redirect, require enrollment, or have changed markup.")
    if status_stop:
        print("Rate limit response received; stopped. Seek owner's approved rate limits before running again.")


if __name__ == "__main__":
    main()
