import json

from collections.abc import Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict

from logging import getLogger

log = getLogger(__name__)


class InferenceResultLoadError(ValueError):
    """Raised when InferenceResult cannot be loaded correctly."""

    pass


class InvalidDataset(ValueError):
    """Raised when expected dataset is invalid. E.g. missing files or folders."""

    pass


class SetupLoadError(ValueError):
    """Raised when Setup cannot be loaded from JSON."""

    pass


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

    def save_as_json(self, file_path: str | None = None, indent=4):
        """Save results as a JSON"""
        json_string = self.to_json(indent)

        if not file_path:
            file_path = "results_" + self.model + "_" + self.end_time + ".json"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_string)
        return file_path

    @classmethod
    def from_dict(cls, dict_data: Dict):
        """Create InferenceResult from dictionary"""
        required_keys = {"prompts", "model", "answers", "end_time"}

        if not required_keys.issubset(dict_data.keys()):
            missing = required_keys - dict_data.keys()
            raise InferenceResultLoadError(f"Missing required keys: {missing}")

        if not isinstance(dict_data["answers"], list):
            raise InferenceResultLoadError("'answers' must be a list")

        answers: List[AnswerItem] = []
        for i, ans in enumerate(dict_data["answers"]):
            if not isinstance(ans, dict) or {"problem", "answer"} - set(ans.keys()):
                raise InferenceResultLoadError(f"Invalid answer item at index {i}")
            answers.append(AnswerItem(problem=ans["problem"], answer=ans["answer"]))

        instance = cls(
            prompts=dict_data["prompts"], model=dict_data["model"], answers=answers
        )

        instance.end_time = dict_data["end_time"]
        return instance

    @classmethod
    def from_json_string(cls, json_data: str):
        """Create InferenceResult from JSON string"""
        try:
            data = json.loads(json_data)
        except JSONDecodeError as e:
            raise InferenceResultLoadError(f"Invalid JSON: {e}") from e

        return cls.from_dict(data)

    @classmethod
    def load_from_json_file(cls, json_path: str):
        """Load InferenceResult from JSON file"""
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Results file not found: {path}")
        if not path.is_file():
            raise IsADirectoryError(f"Path is not a file: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except JSONDecodeError as e:
            raise InferenceResultLoadError(f"Invalid JSON in {path}: {e}") from e
        except UnicodeDecodeError as e:
            raise InferenceResultLoadError(f"Encoding error in {path}: {e}") from e

        return cls.from_dict(data)


@dataclass
class Setup:
    strategy: str
    prompts: List[str]
    dataset: str
    model: str

    @classmethod
    def load(cls, setup_path: str):
        """Load Setup from file"""
        path = Path(setup_path)
        if not path.is_file():
            raise FileNotFoundError(f"Setup file not found as {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except JSONDecodeError as e:
            raise SetupLoadError(f"Invalid JSON in setup file {path}: {e}") from e

        required_fields = {"strategy", "prompt", "dataset", "model"}
        missing = required_fields - set(data.keys())
        if missing:
            raise SetupLoadError(f"Setup file missing keys: {missing}")

        if not isinstance(data["prompt"], list) or not all(
            isinstance(p, str) for p in data["prompt"]
        ):
            raise SetupLoadError("'prompt' must be a list of strings")

        if not all(
            isinstance(data[field], str) for field in ["model", "dataset", "strategy"]
        ):
            raise SetupLoadError(
                "'model', 'dataset', 'strategy' fields must be strings"
            )

        return cls(
            strategy=data["strategy"],
            prompts=data["prompt"],
            dataset=data["dataset"],
            model=data["model"],
        )


def load_folder(folder: Path) -> List[Path]:
    if not folder.exists():
        raise InvalidDataset(f"Folder does not exist: {folder}")
    if not folder.is_dir():
        raise InvalidDataset(f"Path is not a directory: {folder}")

    files = [file for file in folder.iterdir()]
    files = sorted(files, key=lambda file: file.name)

    return files


def get_descriptions(
    pics: List[Path], ask_model: Callable[[str, Path], str], prompt: str
) -> List[str]:
    answers = []
    for pic in pics:
        answers.append(ask_model(prompt, pic))

    return answers


def get_iterative_concept(
    pics: List[Path], ask_model: Callable[[str, Path], str], prompts: List[str]
) -> str:
    answer = ask_model(prompts[0], pics[0])
    for pair in pics[1:-1]:
        answer = ask_model(prompts[1], pair)

    answer = ask_model(prompts[2], pics[-1])
    return answer


def direct(
    ask_model: Callable[[str, Path], str],
    reload_context: Callable[[], None],
    setup: Setup,
) -> InferenceResult:
    prompts = setup.prompts
    folder_path = Path(setup.dataset)
    tasks_folders = [file for file in folder_path.iterdir()]
    tasks_folders = sorted(tasks_folders, key=lambda folder: folder.name)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        collage = problem / "collage.png"
        if not collage.is_file():
            log.debug("Skipping problem %s: no collage.png", problem.name)
            continue

        reload_context()
        answer = ask_model(prompts[0], problem / "collage.png")
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup.model, answers=answers)


def descriptive_direct(
    ask_model: Callable[[str, Path], str],
    reload_context: Callable[[], None],
    setup: Setup,
) -> InferenceResult:
    prompts = setup.prompts
    single_prompt = prompts[0]
    collage_prompt = prompts[1]

    folder_path = Path(setup.dataset)
    try:
        tasks_folders = load_folder(folder_path)
    except InvalidDataset as e:
        log.error("Dataset folder missing: %s", e)
        return InferenceResult(prompts=prompts, model=setup.model, answers=[])

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        collage = problem / "collage.png"
        if not collage.is_file():
            log.debug("Skipping problem %s: no collage.png", problem.name)
            continue

        try:
            lefts = load_folder(problem / "left")
            rights = load_folder(problem / "right")
        except InvalidDataset:
            log.debug(
                "Skipping problem %s: missing left/right subfolders", problem.name
            )
            continue

        lefts_desc = get_descriptions(lefts, ask_model, single_prompt)
        rights_desc = get_descriptions(rights, ask_model, single_prompt)

        answer = ask_model(collage_prompt.format(lefts_desc, rights_desc), collage)
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup.model, answers=answers)


def descriptive_iterative(
    ask_model: Callable[[str, Path], str],
    reload_context: Callable[[], None],
    setup: Setup,
) -> InferenceResult:
    prompts = setup.prompts
    collage_prompt = prompts[3]

    folder_path = Path(setup.dataset)
    tasks_folders = load_folder(folder_path)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        collage = problem / "collage.png"
        if not collage.is_file():
            log.debug("Skipping problem %s: no collage.png", problem.name)
            continue

        try:
            lefts = load_folder(problem / "left")
            rights = load_folder(problem / "right")
        except InvalidDataset:
            log.debug(
                "Skipping problem %s: missing left/right subfolders", problem.name
            )
            continue

        left_concept = get_iterative_concept(lefts, ask_model, prompts)
        right_concept = get_iterative_concept(rights, ask_model, prompts)

        answer = ask_model(collage_prompt.format(left_concept, right_concept), collage)
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup.model, answers=answers)


def contrastive_direct(
    ask_model: Callable[[str, Path], str],
    reload_context: Callable[[], None],
    setup: Setup,
) -> InferenceResult:
    prompts = setup.prompts
    pair_prompt = prompts[0]
    collage_prompt = prompts[1]

    folder_path = Path(setup.dataset)
    tasks_folders = load_folder(folder_path)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        collage = problem / "collage.png"
        if not collage.is_file():
            log.debug("Skipping problem %s: no collage.png", problem.name)
            continue

        try:
            pairs = load_folder(problem / "pairs")
        except InvalidDataset:
            log.debug("Skipping problem %s: missing pairs subfolder", problem.name)
            continue
        pairs_decs = get_descriptions(pairs, ask_model, pair_prompt)

        answer = ask_model(collage_prompt.format(pairs_decs), collage)
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup.model, answers=answers)


def contrastive_iterative(
    ask_model: Callable[[str, Path], str],
    reload_context: Callable[[], None],
    setup: Setup,
) -> InferenceResult:
    prompts = setup.prompts

    folder_path = Path(setup.dataset)
    tasks_folders = load_folder(folder_path)

    answers = []
    for problem in tqdm(tasks_folders, desc="Solving problems", unit="problem"):
        reload_context()

        try:
            pairs = load_folder(problem / "pairs")
        except InvalidDataset:
            log.debug("Skipping problem %s: missing pairs subfolder", problem.name)
            continue

        answer = get_iterative_concept(pairs, ask_model, prompts)
        answers.append(AnswerItem(problem=problem.name, answer=answer))

    return InferenceResult(prompts=prompts, model=setup.model, answers=answers)
