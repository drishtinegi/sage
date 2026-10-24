import statistics
import sys
from pathlib import Path

import httpx

API = "http://localhost:8000"


def main() -> None:
    topic_id = int(sys.argv[1])
    lines = [l.strip() for l in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if l.strip()]
    with httpx.Client(base_url=API, timeout=180) as c:
        s = c.post("/sessions", json={"topic_id": topic_id}).json()
        sid = s["session_id"]
        print("Beginner:", s["opening"])
        times = []
        for line in lines:
            print("\nYou:", line)
            r = c.post(f"/sessions/{sid}/turns", json={"text": line})
            if r.status_code != 200:
                print(r.status_code, r.text)
                break
            d = r.json()
            times.append(d["seconds"])
            print(f"Beginner: {d['beginner']}  [{d['seconds']}s]")
            if d["ended"]:
                print(f"(session ended: {d['ended_by']})")
                break
        rep = c.post(f"/sessions/{sid}/finish").json()
        print(f"\nScore: {rep['score']}%  ({rep['ended_by']})")
        for i in rep["items"]:
            print(f"{i['position']:>2}. [{i['status'].upper():<7}] {i['text']}")
        if times:
            print(f"\nMedian reply time: {statistics.median(times):.1f}s (target: under 5s)")


if __name__ == "__main__":
    main()