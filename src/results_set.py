import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from reader import load_sorted_data


class ResultSet:
    def __init__(
        self,
        results_path: Path,
        images_folder: Path,
        evaluation_path: Path = Path("evaluation.json"),
        tasks_to_remove: list[str] = [],
    ):
        """
        Инициализация программы
        Args:
            json_path: путь к JSON файлу с результатами
            images_folder: путь к папке с изображениями
            evaluation_path: путь к файлу с отзывами
        """
        self.tasks_to_remove: list[str] = tasks_to_remove
        self.results_path = results_path
        self.images_folder = images_folder
        self.evaluation_path = evaluation_path
        self.data: dict[str, list[dict[str, str]]] = {}  # General data
        self.users: Dict[str, Dict[str, str]] = {}  # Users info
        self.user_tasks: Dict[str, List[Dict[str, str | int]]] = (
            {}
        )  # Tasks answers by users
        self.evaluations: Dict[str, Dict[str, Dict[str, str | int]]] = {}
        # Tasks with evaluations by tasks (tasks[user ids[task responses + evaluation]])

        self.load_results()
        self.load_evaluation()

    def load_results(self):
        if not self.results_path.exists():
            print(f"Ошибка: Файл {self.results_path} не найден!")
            sys.exit(1)

        if not self.images_folder.exists():
            print(f"Ошибка: Папка с изображениями {self.images_folder} не найдена!")
            sys.exit(1)

        if self.results_path.suffix == ".ldj":
            self.data = load_sorted_data(self.results_path)
        else:
            with open(self.results_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

        self._exclude_tasks(self.tasks_to_remove)

        # data setup
        for user_id, records in self.data.items():
            self.user_tasks[user_id] = []

            for i, record in enumerate(records):
                if record.get("response_type") == "form":
                    # Users info
                    self.users[user_id] = {
                        "username": record.get("username", user_id),
                        "age": record.get("age", "N/A"),
                        "sex": record.get("sex", "N/A"),
                        "occupation": record.get("occupation", "N/A"),
                        "start_timestamp": record.get("timestamp", "N/A"),
                        "end_timestamp": records[-1].get("timestamp", "N/A"),
                    }
                elif record.get("response_type") == "task_answer":
                    # Tasks answers by users
                    task_info = {
                        "test_image": record.get("test_image"),
                        "left_answer": record.get("left_answer"),
                        "right_answer": record.get("right_answer"),
                        "time": timestamp_difference(
                            records[i - 1].get("timestamp", "N/A"),
                            record.get("timestamp", "N/A"),
                        ),
                    }
                    self.user_tasks[user_id].append(task_info)
                elif record.get("response_type") == "email_submission":
                    self.users[user_id]["email"] = record["email"]

    def load_evaluation(self):
        if self.evaluation_path.exists():
            with open(self.evaluation_path, "r", encoding="utf-8") as f:
                self.evaluations = json.load(f)
        evaluations = self.evaluations
        for user_id, records in self.data.items():
            for i, record in enumerate(records):
                if record["response_type"] == "task_answer":
                    img_name = record["test_image"]
                    if img_name not in evaluations:
                        evaluations[img_name] = {}
                    if user_id not in evaluations[img_name]:
                        empty_eval = {
                            "user_id": user_id,
                            "username": record["username"],
                            "left_answer": record["left_answer"],
                            "right_answer": record["right_answer"],
                            "time": timestamp_difference(
                                records[i - 1]["timestamp"],
                                record.get("timestamp", "N/A"),
                            ),
                            "evaluation": "",
                        }
                        evaluations[img_name][user_id] = empty_eval

    def _exclude_tasks(self, tasks: list[str]):

        full_data = self.data
        for userid in full_data:
            to_del: list[int] = []
            if tasks:
                for i, task in enumerate(full_data[userid]):
                    if task["response_type"] == "task_answer":
                        if task["test_image"] in tasks:
                            to_del.append(i)
                full_data[userid] = [
                    item
                    for idx, item in enumerate(full_data[userid])
                    if idx not in to_del
                ]


def timestamp_difference(from_timestamp: str, to_timestamp: str) -> int:
    """Difference in seconds for to timestamps"""

    time_from = datetime.strptime(from_timestamp, "%Y%m%dT%H%M%S")
    time_to = datetime.strptime(to_timestamp, "%Y%m%dT%H%M%S")
    seconds_difference = int((time_to - time_from).total_seconds())
    return seconds_difference
