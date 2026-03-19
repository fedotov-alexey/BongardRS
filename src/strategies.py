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
    prompts: List[str]
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
    def from_dict(cls, dict_data):
        """Create InferenceResult from dictionary"""
        answers = [AnswerItem(**ans) for ans in dict_data["answers"]]
        instance = cls(prompt=dict_data["prompts"], model=dict_data["model"], answers=answers)

        instance.end_time = dict_data["end_time"]
        return instance

    @classmethod
    def from_json_string(cls, json_data):
        """Create InferenceResult from JSON string"""
        data = json.loads(json_data)
        return InferenceResult.from_dict(data)
    
    @classmethod
    def load_from_json_file(cls, json_path):
        """Load InferenceResult from JSON file"""
        # load inference results
        with open("results.json", 'r') as f:
            data = json.load(f)



def load_setup(setup_path):
    with open(setup_path, "r") as file:
        setup = json.load(file)
    return setup


def direct(ask_model, reload_context, setup) -> InferenceResult:
    prompts = setup["prompts"]
    folder_path = Path(setup["dataset"])
    tasks_folders = [file for file in folder_path.iterdir()]
    tasks_folders = sorted(tasks_folders, key=lambda folder: folder.name)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        collage = problem / "collage.png"
        if collage.exists():
            reload_context()
            answer = ask_model(prompts[0], problem / "collage.png")
            answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup["model"], answers=answers)

def contrastive_iterative(ask_model, reload_context, setup) -> InferenceResult:
    prompts = setup["prompts"]
    first_prompt = prompts[0]
    iterative_prompt = prompts[1]
    last_prompt = prompts[2]
    
    folder_path = Path(setup["dataset"])
    tasks_folders = [file for file in folder_path.iterdir()]
    tasks_folders = sorted(tasks_folders, key=lambda folder: folder.name)
  
    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        pairs_folder = problem / "pairs"
        if not pairs_folder.exists():
            continue

        pairs = [pair for pair in pairs_folder.iterdir()]
        pairs = sorted(pairs, key=lambda file: file.name)

        answer = ask_model(first_prompt, pairs[0])
        for pair in pairs[1:-1]:
            answer = ask_model(iterative_prompt, pair)

        answer = ask_model(last_prompt, pairs[-1])

        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup["model"], answers=answers)

