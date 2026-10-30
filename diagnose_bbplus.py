#!/usr/bin/env python3
"""Inspect publicly available BBPlus HTML without changing site state.

Reports redirect URLs, page titles, and the count of known quiz HTML elements.
No login, authentication, cookies, private endpoints, or access-control bypasses.
"""
from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
from extract_bbplus import Downloader, normalize, extract_quiz

URLS = [
    "https://bbplus.plus/courses/2023-august/lessons/august-2023-intl-form-a/quizzes/aug2023-form-a-english-m1/",
    "https://bbplus.plus/courses/2025-december/lessons/december-2025-intl-form-a/quizzes/dec2025-intl-form-a-english-m1/",
]
SELECTORS = [
    ".wpProQuiz_question",
    ".wpProQuiz_question_text",
    ".wpProQuiz_questionList",
    ".wpProQuiz_questionListItem",
    "[class*='wpProQuiz']",
    "[class*='question']",
    ".learndash-wrapper",
]

def diagnose(url: str, dl: Downloader) -> None:
    url = normalize(url)
    if not url:
        print('Disallowed URL, must be a BBPlus quiz URL.')
        return
    print(f"\nREQUESTED: {url}")
    status, data, final = dl.get(url)
    print(f"RESULT:    {status}")
    print(f"FINAL URL: {final}")
    if status != "ok" or not data:
        return
    soup = BeautifulSoup(data, 'html.parser')
    print(f"TITLE:     {(soup.title.get_text(' ', strip=True) if soup.title else 'none')[:120]}")
    print(f"HTML BYTES: {len(data):,}")
    for selector in SELECTORS:
        print(f"  {selector}: {len(soup.select(selector))}")
    parsed = extract_quiz(data.decode('utf-8', 'replace'), final)
    print(f"EXTRACTED: {len(parsed)}")
    print(f"QUESTION NUMBERS: {[q['number'] for q in parsed[:5]]}")
    t = soup.get_text(' ', strip=True).lower()
    closed = any(phrase in t for phrase in ("this practice exam is currently closed", "you don't currently have access to this content"))
    print(f"CLOSED MESSAGE: {closed}")
    print(f"LOGIN PROMPT: {('you must sign in or sign up to start' in t)}")
    if not parsed and any(soup.select(s) for s in SELECTORS[:4]):
        print('NOTE: Quiz elements exist but parser found none; selector/nesting fix needed.')
    if not parsed and not any(soup.select(s) for s in SELECTORS[:4]):
        print('NOTE: No LearnDash quiz elements present; possible closed course, lazy-loaded content, or alternate markup.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('urls', nargs='*', help='Optional URLs to check instead of two defaults')
    parser.add_argument('--delay', type=float, default=3.0)
    args = parser.parse_args()
    dl = Downloader(args.delay)
    for u in (args.urls or URLS):
        diagnose(u, dl)
