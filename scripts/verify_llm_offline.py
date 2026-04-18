from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.infrastructure.llm import PromptBuilder, ResponseParser


def main() -> None:
    p = PromptBuilder().build("SOURCE", ["k1", "k2"], "tmpl")
    print("prompt_ok=", ("k1" in p and "SOURCE" in p))

    out = '{"k1":"v1","k2":""}'
    parsed = ResponseParser().parse_and_validate(out, ["k1", "k2"])
    print(parsed)


if __name__ == "__main__":
    main()

