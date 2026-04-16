import json

from codecs import encode
from pathlib import Path
from typing import Any


class HumanAnswerItem:
    problem: str
    answer: str
    seed: str


def clean_data(
    input_file: Path,
    dump: bool = True,
    output_file: Path = Path("parsed_data"),
    timestamp: str = "20260402T165704",
) -> list[dict[str, str | int]]:
    """
    Parse experiment data from JSONL format, extract only the response data
    and relevant metadata, and save to a clean JSON file.
    """

    parsed_data: list[dict[str, str | int]] = []

    with open(input_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("ts") < timestamp:
                    continue

                # Extract only the data we need
                extracted: dict[str, str | int] = {
                    "username": record.get("username"),
                    "timestamp": record.get("ts"),
                    "seed": record.get("seed"),
                }

                # Extract response data
                response = record.get("response", {})

                # Check if this is a questionnaire response (has age, occupation, sex)
                if "age" in response or "occupation" in response or "sex" in response:
                    extracted["response_type"] = "form"
                    extracted["age"] = response.get("age", "")
                    extracted["sex"] = response.get("sex", "")
                    extracted["occupation"] = response.get("occupation", "")

                # Check if this is an answer to a task (has left_ans and right_ans)
                elif "left_ans" in response or "right_ans" in response:
                    extracted["response_type"] = "task_answer"
                    extracted["left_answer"] = response.get("left_ans", "")
                    extracted["right_answer"] = response.get("right_ans", "")

                # Check if this is a "don't know" response
                elif response.get("response") == "Не знаю":
                    extracted["response_type"] = "dont_know"
                    extracted["left_answer"] = "Не знаю"
                    extracted["right_answer"] = "Не знаю"

                # Check if this is instruction navigation
                elif response.get("response") in [
                    "Продолжить",
                    "Перейти к решению задач",
                ]:
                    continue

                # Check if this is email submission
                elif "email" in response:
                    extracted["response_type"] = "email_submission"
                    extracted["email"] = response.get("email", "")

                # Extract test frame path if exists
                test = record.get("test", {})
                frames = test.get("frames", [])
                if frames and len(frames) > 0:
                    encoded_path = frames[0].get("path", "")
                    extracted["test_image"] = encode(encoded_path, "rot_13")

                parsed_data.append(extracted)

            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue

    # Save to JSON file
    if dump:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)

        print(f"Successfully parsed {len(parsed_data)} records")
        print(f"Data saved to {output_file}")
    return parsed_data


def sort_data(
    clean_data: list[Any],
    full: bool = True,
    dump: bool = True,
    output_path: Path = Path("sorted_data.json"),
) -> dict[str, list[dict[str, str | int]]]:
    """
    Full: return only completed tests
    """
    unique_users: dict[str, list[dict[str, str | int]]] = {}
    entry_amount: int = 22
    for item in clean_data:
        id = str(item["seed"]) + item["username"]
        if id not in unique_users:
            unique_users[id] = []
        unique_users[id].append(item)
    if full:
        to_del: list[str] = []
        for key, value in unique_users.items():
            if len(value) != entry_amount:
                to_del.append(key)
                print(f"{key} did not complete the experiment")
        [unique_users.pop(key) for key in to_del]
    if dump:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_users, f, ensure_ascii=False, indent=2)
    return unique_users


def load_sorted_data(
    input_file: Path, timestamp: str = "20260402T165704"
) -> dict[str, list[dict[str, str | int]]]:
    parsed_data = clean_data(input_file, dump=False, timestamp=timestamp)
    sorted_data = sort_data(
        parsed_data, full=True, dump=True, output_path=Path("grouped_relevant.json")
    )
    return sorted_data


if __name__ == "__main__":

    folder = "bongard_0303_test"
    input_file = "data/Bongard_0303.ldj"  # Change this to your input file path

    Path("data/" + folder).mkdir(parents=True, exist_ok=True)

    group_file = "data/" + folder + "/grouped_data.json"
    summary_file = "data/" + folder + "/data_summary.json"

    # Parse and clean the data
    parsed_data = clean_data(input_file, dump=False, timestamp="20260402T165704")
    sorted_data = sort_data(parsed_data, full=True, dump=True, output_path=group_file)

    print("\nDone! Files created:")
    print(f"  - {summary_file}: Statistics summary")
