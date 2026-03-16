import json

from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from typing import List


@dataclass
class AnswerItem:
    problem: str
    answer: str


@dataclass
class InferenceResult:
    prompt: str
    model: str
    answers: List[AnswerItem]
    end_time: str = field(init=False)

    def __post_init__(self):
        self.end_time = datetime.now().isoformat()

    def to_json(self, file_path=None, indent=4):
        """Serialize results as a json-formatted string and save as a JSON"""
        json_data = json.dumps(asdict(self), indent=indent, ensure_ascii=False)

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_data)
            return file_path

        return json_data

    @classmethod
    def from_json(cls, json_data):
        """Create InferenceResult from JSON string or dict"""
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        answers = [AnswerItem(**ans) for ans in data["answers"]]
        instance = cls(prompt=data["prompt"], model=data["model"], answers=answers)

        instance.end_time = data["end_time"]
        return instance


def load_setup(setup_path):
    with open(setup_path, "r") as file:
        setup = json.load(file)
    return setup


def direct(ask_model, reload_context, setup) -> InferenceResult:
    cur_prompt = setup["prompt"]
    folder_path = Path(setup["dataset"])
    tasks_folders = [file for file in folder_path.iterdir()]
    tasks_folders = sorted(tasks_folders, key=lambda folder: folder.name)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()
        answer = ask_model(cur_prompt, problem / "collage.png")
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompt=cur_prompt, model=setup["model"], answers=answers)
