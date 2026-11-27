"""Write the cumulative series for the 27 November rule A figure to stdout.

Input: indexus/core e4b90728, docs/benchmarks/aws-placement-100-20261127/
granular50/aws-pair-a.json.gz. Each archived episode is one donor–target pair.
Rebuild: python3 data/extract_service.py PATH/aws-pair-a.json.gz > data/service-a.csv
"""
import csv
import gzip
import json
import sys


def main():
    with gzip.open(sys.argv[1], "rt", encoding="utf-8") as source:
        trace = json.load(source)
    window = trace["window"]
    requested = []
    writing = []
    for episode in trace["episodes"]:
        first = episode["attempts"][0][0]
        if 0 <= first < window:
            requested.append(first)
            write = episode["write"]
            if episode["hook"] is not None and write is not None and first <= write <= window:
                writing.append(write)
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("seconds", "requested_pairs", "pairs_with_receiver_write"))
    for t in range(0, window + 1, 10):
        writer.writerow((t, sum(v <= t for v in requested), sum(v <= t for v in writing)))


if __name__ == "__main__":
    main()
