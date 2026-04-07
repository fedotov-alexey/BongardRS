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

    def to_json(self, indent=4):
        """Serialize results as a json-formatted string"""
        json_data = json.dumps(asdict(self), indent=indent, ensure_ascii=False)

        return json_data

    def save_as_json(self, file_path=None, indent=4):
        """Save results as a JSON"""
        json_string = self.to_json(indent)

        if not file_path:
            file_path = "results_" + self.model + "_" + self.end_time + ".json"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_string)
        return file_path

    @classmethod
    def from_dict(cls, dict_data):
        """Create InferenceResult from dictionary"""
        answers = [AnswerItem(**ans) for ans in dict_data["answers"]]
        instance = cls(
            prompt=dict_data["prompts"], model=dict_data["model"], answers=answers
        )

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
        with open("results.json", "r") as f:
            data = json.load(f)


def load_setup(setup_path):
    with open(setup_path, "r") as file:
        setup = json.load(file)
    return setup

def load_folder(folder: Path) -> List[Path] | None:
    if not folder.exists():
        return None

    files = [file for file in folder.iterdir()]
    files = sorted(files, key=lambda file: file.name)

    return files

def get_descriptions(pics: List[Path], ask_model, prompt: str) -> List[str]:
    answers = []
    for pic in pics:
        answers.append(ask_model(prompt, pic))

    return answers

def get_iterative_concept(pics: List[Path], ask_model, prompts: List[str]) -> str:
    answer = ask_model(prompts[0], pics[0])
    for pair in pics[1:-1]:
        answer = ask_model(prompts[1], pair)

    answer = ask_model(prompts[2], pics[-1])
    return answer

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

def descriptive_direct(ask_model, reload_context, setup) -> InferenceResult:
    prompts = setup["prompts"]
    single_prompt = prompts[0]
    collage_prompt = prompts[1]

    folder_path = Path(setup["dataset"])
    tasks_folders = load_folder(folder_path)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        collage = problem / "collage.png"
        if not collage.exists():
            continue

        lefts = load_folder(problem / "left")
        rights = load_folder(problem / "right")

        lefts_desc = get_descriptions(lefts, ask_model, single_prompt)
        rights_desc = get_descriptions(rights, ask_model, single_prompt)

        answer = ask_model(collage_prompt.format(lefts_desc, rights_desc), collage)
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup["model"], answers=answers)

def descriptive_iterative(ask_model, reload_context, setup) -> InferenceResult:
    prompts = setup["prompts"]
    first_prompt = prompts[0]
    iterative_prompt = prompts[1]
    last_prompt = prompts[2]
    collage_prompt = prompts[3]

    folder_path = Path(setup["dataset"])
    tasks_folders = load_folder(folder_path)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        collage = problem / "collage.png"
        if not collage.exists():
            continue

        lefts = load_folder(problem / "left")
        rights = load_folder(problem / "right")

        left_concept = get_iterative_concept(lefts, ask_model, prompts)
        right_concept = get_iterative_concept(rights, ask_model, prompts)

        answer = ask_model(collage_prompt.format(left_concept, right_concept), collage)
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup["model"], answers=answers)

def contrastive_direct(ask_model, reload_context, setup) -> InferenceResult:
    prompts = setup["prompts"]
    pair_prompt = prompts[0]
    collage_prompt = prompts[1]

    folder_path = Path(setup["dataset"])
    tasks_folders = load_folder(folder_path)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        collage = problem / "collage.png"
        if not collage.exists():
            continue

        pairs = load_folder(problem / "pairs")
        pairs_decs = get_descriptions(pairs, ask_model, pair_prompt)

        answer = ask_model(collage_prompt.format(pairs_decs), collage)
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup["model"], answers=answers)


def contrastive_iterative(ask_model, reload_context, setup) -> InferenceResult:
    prompts = setup["prompts"]

    folder_path = Path(setup["dataset"])
    tasks_folders = load_folder(folder_path)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        pairs = load_folder(problem / "pairs")

        answer = get_iterative_concept(pairs, ask_model, prompts)
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup["model"], answers=answers)
