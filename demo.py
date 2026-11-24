#!/usr/bin/env python3
"""Replay a synthetic local request as an NDJSON event stream."""
import argparse
import json
import time

# input tokens, queue milliseconds, prefill milliseconds, inter-token milliseconds
CASES = {
    "baseline": (128, 20, 40, 30),
    "queue": (128, 400, 40, 30),
    "long-input": (4096, 20, 900, 30),
    "decode": (128, 20, 40, 180),
}


def events(case, count):
    input_tokens, queue, prefill, interval = CASES[case]
    first = queue + prefill
    yield {"event": "request", "scenario": case, "t_ms": 0,
           "input_tokens": input_tokens, "synthetic": True}
    yield {"event": "prefill_start", "t_ms": queue}
    yield {"event": "prefill_end", "t_ms": first}
    for index in range(count):
        yield {"event": "token", "t_ms": first + interval * index, "index": index + 1}
    yield {"event": "done", "t_ms": first + interval * (count - 1)}


def summarize(stream):
    phase = {e["event"]: e["t_ms"] for e in stream if e["event"] != "token"}
    tokens = [e["t_ms"] for e in stream if e["event"] == "token"]
    return {"event": "metrics", "ttft_ms": tokens[0] - phase["request"],
            "tpot_ms": (tokens[-1] - tokens[0]) / (len(tokens) - 1) if len(tokens) > 1 else None,
            "queue_ms": phase["prefill_start"] - phase["request"],
            "prefill_ms": phase["prefill_end"] - phase["prefill_start"],
            "output_tokens": len(tokens), "synthetic": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    parser.add_argument("--tokens", type=int, default=5)
    parser.add_argument("--realtime", action="store_true",
                        help="pace stdout with the simulated clock; still not a benchmark")
    args = parser.parse_args()
    if not 1 <= args.tokens <= 1000:
        parser.error("--tokens must be between 1 and 1000")
    start = time.monotonic()
    stream = []
    for event in events(args.case, args.tokens):
        if args.realtime:
            time.sleep(max(0, start + event["t_ms"] / 1000 - time.monotonic()))
        print(json.dumps(event, separators=(",", ":")), flush=True)
        stream.append(event)
    print(json.dumps(summarize(stream), separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
