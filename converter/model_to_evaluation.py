import argparse
import json
from pathlib import Path
from typing import Any, Literal, TypeAlias, TypedDict

from pydantic import BaseModel


class CleanedAnswer(TypedDict):
    username: str
    timestamp: str | None
    seed: str | None
    strategy: str
    modelname: str | None
    test_image: str
    response_type: Literal["task_answer"]
    left_answer: str | None
    right_answer: str | None

class EvaluationEntry(BaseModel):
    user_id: str
    username: str
    modelname: str | None
    strategy: str
    left_answer: str | None
    right_answer: str | None
    time: int = 0
    evaluation: str = ""

Evaluations: TypeAlias = dict[str, dict[str, dict[str, str | int | None]]]


def load_json(input_file: Path) -> Any:
    with open(input_file, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid model results JSON in {input_file}: {e}") from e


def clean_data(record: dict[str, Any]) -> list[CleanedAnswer]:
    """Extract answer records from decoded model results."""
    parsed_data: list[CleanedAnswer] = []
    model = record.get("model")
    end_time = record.get("end_time")
    for strategy in record["results"]:
        for answer in strategy["answers"]:
            parsed_data.append({
                "username": f"{model}, {strategy['strategy']}",
                "timestamp": end_time,
                "seed": end_time,
                "strategy": strategy["strategy"],
                "modelname": model,
                "test_image": f"{answer.get('problem')}.png",
                "response_type": "task_answer",
                "left_answer": answer.get("answer", ""),
                "right_answer": answer.get("answer", ""),
            })
    return parsed_data

def group_by_user_id(
    clean_data: list[CleanedAnswer],
    full: bool = True,
    entry_amount: int = 22
) -> dict[str, list[CleanedAnswer]]:
    """
    Full: return only completed tests
    """
    unique_users: dict[str, list[CleanedAnswer]] = {}
    for item in clean_data:
        id = str(item["seed"]) + item["username"]
        if id not in unique_users:
            unique_users[id] = []
        unique_users[id].append(item)
    if full:
        return {key: rows for key, rows in unique_users.items() if len(rows) >= entry_amount}
    return unique_users


def _add_evaluations(
    evaluations: Evaluations, records_by_user: dict[str, list[CleanedAnswer]]
) -> None:
    """Index answers by image and user ID, keeping the first answer for each pair."""
    for user_id, records in records_by_user.items():
        for record in records:
            image = record["test_image"]
            answers_by_user = evaluations.setdefault(image, {})
            if user_id in answers_by_user:
                continue

            entry = EvaluationEntry.model_validate({**record, "user_id": user_id})
            answers_by_user[user_id] = entry.model_dump()


def _convert_files(input_files: list[Path]) -> Evaluations:
    evaluations: Evaluations = {}
    for input_file in input_files:
        try:
            records = clean_data(load_json(input_file))
            records_by_user = group_by_user_id(records, full=False)
            _add_evaluations(evaluations, records_by_user)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Cannot convert {input_file}: {exc}") from exc
    if not evaluations:
        raise ValueError("No model answers found; no evaluation file written")
    return evaluations


def dump_json(data: Any, output: Path) -> None:
    """Write data to a new JSON file."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def convert_directory(
    input_dir: str | Path, recursive: bool = False
) -> Evaluations:
    """Combine raw *.json files in sorted path order into one evaluation dictionary.

    Set recursive=True to include subdirectories. All JSON files must use the raw model results format.
    Duplicate task/user pairs retain the first answer.
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise ValueError(f"Not a directory: {input_dir}")
    paths = input_dir.rglob("*.json") if recursive else input_dir.glob("*.json")
    input_files = sorted(p for p in paths if p.is_file())
    return _convert_files(input_files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Raw model results JSON or directory of raw JSON files")
    parser.add_argument("output", type=Path, help="New evaluation JSON (must not exist)")
    parser.add_argument("--recursive", action="store_true", help="Include subdirectories of the input directory")
    args = parser.parse_args()
    try:
        if args.output.exists():
            parser.error(f"Output already exists: {args.output}")
        if args.input.is_dir():
            evaluations = convert_directory(args.input, args.recursive)
        elif args.recursive:
            parser.error("--recursive requires an input directory")
        else:
            evaluations = _convert_files([args.input])
        dump_json(evaluations, args.output)
        count = sum(len(responses) for responses in evaluations.values())
        print(f"Saved {count} answers across {len(evaluations)} tasks to {args.output}")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
