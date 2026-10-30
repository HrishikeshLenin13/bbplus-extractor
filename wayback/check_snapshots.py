import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

out = Path("wayback")
out.mkdir(exist_ok=True)

domains = ["bluebook.plus", "bbplus.plus"]
records = []
failures = []

for domain in domains:
    print(f"\nSearching archived pages for {domain}...")

    params = {
        "url": domain,
        "matchType": "domain",
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype",
        "filter": "statuscode:200",
        "collapse": "urlkey",
        "limit": "5000"
    }

    url = (
        "https://web.archive.org/cdx/search/cdx?"
        + urllib.parse.urlencode(params)
    )

    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read().decode("utf-8")

        data = json.loads(body)

        if data:
            headers = data[0]
            for row in data[1:]:
                item = dict(zip(headers, row))
                item["domain"] = domain
                item["snapshot"] = (
                    "https://web.archive.org/web/"
                    + item["timestamp"] + "/"
                    + item["original"]
                )
                records.append(item)

        print(f"Found {max(0, len(data)-1)} captures")

    except Exception as exc:
        failures.append(domain)
        print(f"Archive query failed: {exc}")

    time.sleep(2)

fields = [
    "domain", "timestamp", "original",
    "statuscode", "mimetype", "snapshot"
]

with (out / "snapshots.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)

keywords = [
    "question", "quiz", "test", "practice",
    "drill", "reading", "math", "module",
    "sat", "question-bank", "assessment"
]

def rank(record):
    path = urllib.parse.urlsplit(
        record["original"]
    ).path.lower()
    return sum(word in path for word in keywords)

promising = sorted(
    [r for r in records if rank(r) > 0],
    key=rank,
    reverse=True
)

with (out / "promising_snapshots.txt").open("w") as f:
    for r in promising:
        f.write(r["snapshot"] + "\n")

print("\n========= RESULTS =========")
print("Total indexed captures:", len(records))
print("Promising page URLs:", len(promising))
print("Failed domain queries:", failures)
print("Saved index: wayback/snapshots.csv")
print("Saved candidates: wayback/promising_snapshots.txt")

for r in promising[:10]:
    print(r["snapshot"])

if failures:
    print("\nSome archive queries failed.")
    print("Do not interpret these failures as zero captures.")
