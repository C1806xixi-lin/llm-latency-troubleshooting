"""Exercise the same CLI readers run in the README."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CASES = {"baseline": (60, 30, 20, 40), "queue": (440, 30, 400, 40),
         "long-input": (920, 30, 20, 900), "decode": (60, 180, 20, 40)}


def run(*args):
    return subprocess.run([sys.executable, str(ROOT / "demo.py"), *args],
                          capture_output=True, text=True, timeout=10)


class DemoTests(unittest.TestCase):
    def test_cli_fixtures_and_chart(self):
        chart = ET.parse(ROOT / "assets" / "ttft-tpot.svg")
        for case, target in CASES.items():
            with self.subTest(case=case):
                result = run(case)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, (ROOT / "examples" / f"{case}.jsonl").read_text())
                *stream, summary = map(json.loads, result.stdout.splitlines())
                times = [e["t_ms"] for e in stream]
                self.assertEqual(times, sorted(times))
                self.assertEqual([e["index"] for e in stream if e["event"] == "token"],
                                 list(range(1, 6)))
                self.assertTrue(stream[0]["synthetic"])
                self.assertEqual(stream[-1]["event"], "done")
                self.assertEqual(tuple(summary[key] for key in
                    ("ttft_ms", "tpot_ms", "queue_ms", "prefill_ms")), target)
                for metric, value in zip(("ttft", "tpot"), target):
                    bar = chart.find(f".//*[@id='{metric}-{case}']")
                    self.assertEqual(int(bar.get("width")), value // 2 if metric == "ttft" else value)
                    label = chart.find(f".//*[@id='{metric}-{case}-label']")
                    self.assertEqual(label.text, str(value))

    def test_one_token_tpot_is_undefined(self):
        result = run("decode", "--tokens", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual((summary["ttft_ms"], summary["tpot_ms"], summary["output_tokens"]),
                         (60, None, 1))

    def test_invalid_count_fails_without_partial_event_stream(self):
        result = run("baseline", "--tokens", "0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--tokens must be between 1 and 1000", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_realtime_pacing_does_not_change_the_trace(self):
        self.assertEqual(run("baseline", "--realtime").stdout, run("baseline").stdout)


if __name__ == "__main__":
    unittest.main()
