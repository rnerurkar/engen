"""CLI: python -m prs_scanner.cli --generated <dir> --blueprint <json>"""
import argparse
import sys

from .scanner import scan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated", required=True)
    ap.add_argument("--blueprint", required=True)
    args = ap.parse_args()
    result = scan(args.generated, args.blueprint)
    for f in result.findings:
        print(f"[{f.severity}] {f.rule} {f.file}: {f.message}")
    print(f"\nPRS scan {'PASSED' if result.passed else 'FAILED'} "
          f"({sum(1 for x in result.findings if x.severity=='critical')} critical)")
    sys.exit(result.exit_code())


if __name__ == "__main__":
    main()
