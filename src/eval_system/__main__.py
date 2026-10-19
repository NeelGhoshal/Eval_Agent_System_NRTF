"""Run: python -m eval_system [path-to-document.txt]   (from the src/ directory)"""
import json
import sys

from .graph import build_graph
from .observability import init_sentry


def main() -> None:
    init_sentry()
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            document = f.read()
    else:
        document = "Sample document text."
    result = build_graph().invoke({"document": document})
    print(json.dumps(result["report"], indent=2))


if __name__ == "__main__":
    main()
