import json
import os
import subprocess
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, Literal
from copy import deepcopy
import time
from results_set import ResultSet, timestamp_difference


class TestResultsViewer:
    def __init__(
        self,
        results_path: Path,
        images_folder: Path,
        evaluation_path: Path = Path("evaluation.json"),
    ) -> None:
        tasks_to_remove = ["bb_m_99.png", "bb_s_38.png", "bb_m_48.png"]
        self.results_path = results_path
        self.images_folder = images_folder
        self.evaluation_path = evaluation_path
        results = ResultSet(
            results_path, images_folder, evaluation_path, tasks_to_remove
        )
        self.data = results.data
        self.users = results.users
        self.user_tasks = results.user_tasks
        self.evaluations = results.evaluations

    def show_image(self, image_name: str):
        """Show image"""
        image_path = self.images_folder / image_name

        if not image_path.exists():
            print(f"  Предупреждение: Изображение {image_name} не найдено!")
            return False

        if sys.platform == "win32":
            os.startfile(image_path)
        elif sys.platform == "darwin":  # macOS
            subprocess.run(["open", image_path])
        else:  # Linux
            try:
                current_window = (
                    subprocess.check_output(["xdotool", "getactivewindow"])
                    .decode()
                    .strip()
                )

                subprocess.Popen(["xdg-open", image_path])
                time.sleep(0.5)

                new_window = (
                    subprocess.check_output(["xdotool", "getactivewindow"])
                    .decode()
                    .strip()
                )

                screen_width = int(
                    subprocess.check_output(["xdotool", "getdisplaygeometry"])
                    .decode()
                    .split()[0]
                )

                # move window
                subprocess.run(
                    [
                        "wmctrl",
                        "-i",
                        "-r",
                        new_window,
                        "-e",
                        f"0,{screen_width // 2},0,{screen_width // 2},-1",
                    ]
                )

                subprocess.run(["xdotool", "windowactivate", current_window])

                print(f"  Изображение открыто справа, фокус возвращен")

            except Exception as e:
                print(f"  Ошибка при управлении окнами: {e}")
                print(
                    f"  Установите wmctrl и xdotool: sudo apt-get install wmctrl xdotool"
                )
                # Fallback
                subprocess.Popen(["xdg-open", image_path])

        return True

    def show_image_with_responses(self):
        """Display 1 problem and all answers with simple navigation"""
        print("\n" + "=" * 60)
        print("ПРОСМОТР ИЗОБРАЖЕНИЯ И ОТВЕТОВ")
        print("=" * 60)
        evaluations = self.evaluations
        images = sorted(evaluations.keys())
        if not images:
            print("Нет данных об ответах на изображения!")
            return

        current_idx = 0

        print("\nДоступные изображения:")
        for i, img in enumerate(images, 1):
            response_count = len(evaluations[img])
            print(f"  {i}. {img} (ответов: {response_count})")

        while True:
            # Clear screen (optional)
            print("\033[2J\033[H")  # ANSI clear screen

            print("\n" + "=" * 60)
            print(
                f"ПРОСМОТР ИЗОБРАЖЕНИЯ И ОТВЕТОВ - {current_idx + 1} из {len(images)}"
            )
            print("=" * 60)

            selected_image = images[current_idx]

            # Open image
            print(f"\nОткрываю изображение: {selected_image}")
            self.show_image(selected_image)

            # Show responses
            responses = evaluations[selected_image]
            print(f"\nОтветы на изображение '{selected_image}':")
            print("-" * 50)

            for i, resp in enumerate(responses.values(), 1):
                print(f"{i}. Пользователь: {resp['username']}")
                print(f"   Левый ответ: {resp['left_answer']}")
                print(f"   Правый ответ: {resp['right_answer']}")
                print()

            print("-" * 50)
            print("\nНавигация:")
            print("  n - следующее изображение")
            print("  p - предыдущее изображение")
            print("  q - выход")
            print("  # - введите номер изображения")

            choice = input("\nВаш выбор: ").strip().lower()

            if choice == "q":
                break
            elif choice == "n" and current_idx < len(images) - 1:
                current_idx += 1
            elif choice == "p" and current_idx > 0:
                current_idx -= 1
            elif choice.isdigit():
                num = int(choice) - 1
                if 0 <= num < len(images):
                    current_idx = num
                else:
                    print(f"Неверный номер! Выберите от 1 до {len(images)}")
                    input("Нажмите Enter...")

    def show_user_images_and_responses(self):
        """Displays problems of 1 test subject"""
        print("\n" + "=" * 60)
        print("ПРОСМОТР ОТВЕТОВ ПОЛЬЗОВАТЕЛЯ")
        print("=" * 60)

        users_list = list(self.users.keys())
        if not users_list:
            print("Нет данных о пользователях!")
            return

        print("\nДоступные пользователи:")
        for i, user_id in enumerate(users_list, 1):
            user_info = self.users[user_id]
            print(
                f"  {i}. {user_info['username']} (возраст: {user_info['age']}, пол: {user_info['sex']})"
            )

        while True:
            try:
                choice = input(
                    f"\nВыберите пользователя (1-{len(users_list)}) или 'q' для выхода: "
                ).strip()
                if choice.lower() == "q":
                    return

                idx = int(choice) - 1
                if 0 <= idx < len(users_list):
                    selected_user = users_list[idx]
                    break
                else:
                    print(f"Пожалуйста, выберите число от 1 до {len(users_list)}")
            except ValueError:
                print("Пожалуйста, введите корректное число")

        tasks = self.user_tasks.get(selected_user, [])
        if not tasks:
            raise ValueError(
                f"У пользователя {self.users[selected_user]['username']} нет ответов на задачи!"
            )

        user_info = self.users[selected_user]
        print(f"\nПользователь: {user_info['username']}")
        print(
            f"Возраст: {user_info['age']}, Пол: {user_info['sex']}, Род занятий: {user_info['occupation']}"
        )
        print(f"Всего заданий: {len(tasks)}")
        print("\nСписок заданий:")
        print("-" * 50)

        for i, task in enumerate(tasks, 1):
            print(f"{i}. Изображение: {task['test_image']}")
            print(f"   Ответ: {task['left_answer']} / {task['right_answer']}")
            print(f"   Время: {task['time']} сек")
            print()

        while True:
            try:
                choice = input(
                    f"\nВыберите задание для просмотра изображения (1-{len(tasks)}) или 'a' для всех, 'q' для выхода: "
                ).strip()
                if choice.lower() == "q":
                    return
                elif choice.lower() == "a":
                    # Показываем все изображения
                    print("\nОткрываю все изображения...")
                    for task in tasks:
                        print(f"Открываю: {task['test_image']}")
                        self.show_image(task["test_image"])
                    break
                else:
                    idx = int(choice) - 1
                    if 0 <= idx < len(tasks):
                        selected_task = tasks[idx]
                        print(f"\nОткрываю изображение: {selected_task['test_image']}")
                        self.show_image(selected_task["test_image"])
                        print(
                            f"Ответ: {selected_task['left_answer']} / {selected_task['right_answer']}"
                        )
                        input("\nНажмите Enter для продолжения...")
                    else:
                        print(f"Пожалуйста, выберите число от 1 до {len(tasks)}")
            except ValueError:
                print("Пожалуйста, введите корректное число")

    def statistics_menu(self):
        """Stats menu"""
        while True:
            print("\n" + "=" * 60)
            print("СТАТИСТИКА")
            print("=" * 60)
            print("\n1. Общая статистика")
            print("2. Статистика по пользователям")
            print("3. Статистика по задачам (изображениям)")
            print("4. Назад в главное меню")

            choice = input("\nВыберите пункт меню (1-4): ").strip()

            if choice == "1":
                self.show_general_stats()
            elif choice == "2":
                self.show_user_stats()
            elif choice == "3":
                self.show_task_stats()
            elif choice == "4":
                break
            else:
                print("Пожалуйста, выберите пункт от 1 до 4")

    def show_general_stats(self):
        """General stats"""
        print("\n" + "-" * 50)
        print("ОБЩАЯ СТАТИСТИКА")
        print("-" * 50)

        total_users = len(self.users)
        total_tasks = sum(len(tasks) for tasks in self.user_tasks.values())
        total_images = len(self.evaluations)
        male_count = sum(1 for u in self.users.values() if u["sex"].lower() == "m")
        female_count = sum(1 for u in self.users.values() if u["sex"].lower() == "f")
        emails = sum(1 for u in self.users.values() if "@" in u["email"].lower())
        ages = [int(u["age"]) for u in self.users.values() if u["age"].isdigit()]
        avg_age = sum(ages) / len(ages) if ages else 0
        evals = self.evaluations
        tasks_correct = 0.0
        for task in evals:
            tasks_correct += calc_correct_task(evals[task])
        norm_correct = tasks_correct / len(evals) * 100
        tasks_correct, tasks_wrong, tasks_other, tasks_unrated = 0, 0, 0, 0

        for task in evals:
            for user in evals[task]:
                if evals[task][user]["evaluation"] == "y":
                    tasks_correct += 1
                elif evals[task][user]["evaluation"] == "n":
                    tasks_wrong += 1
                elif evals[task][user]["evaluation"] == "":
                    tasks_unrated += 1
                else:
                    tasks_other += 1
        total_tasks = tasks_correct + tasks_wrong + tasks_other + tasks_unrated
        checked_tasks = tasks_correct + tasks_wrong + tasks_other
        correct_wrong_total = tasks_correct + tasks_wrong
        checked_percent = (checked_tasks / total_tasks * 100) if total_tasks else 0
        correct_percent_total = (
            (tasks_correct / total_tasks * 100) if total_tasks else 0
        )
        correct_percent_checked = (
            (tasks_correct / checked_tasks * 100) if checked_tasks else 0
        )
        correct_percent_cw = (
            (tasks_correct / correct_wrong_total * 100) if correct_wrong_total else 0
        )

        print(f"\nВсего пользователей: {total_users}")
        print(f"Всего собрано ответов: {total_tasks}")
        print(f"Всего email адресов: {emails}")
        print(f"Уникальных задач: {total_images}")
        print(
            f"Количество проверенных ответов: {checked_tasks} ({checked_percent:.2f}%)"
        )
        print(f"Верные ответы от всех: {tasks_correct} ({correct_percent_total:.2f}%)")
        print(
            f"Верные от проверенных: {tasks_correct} ({correct_percent_checked:.2f}%)"
        )
        print(
            f"Верные из имеющих точную оценку: {tasks_correct} ({correct_percent_cw:.2f}%)"
        )
        print(
            f"Нормализованный процент верных решений: ({norm_correct:.2f}%) \n(C учетом разного количества ответов на разные задачи)"
        )
        print(f"\nДемография:")
        print(f"  Мужчины: {male_count}")
        print(f"  Женщины: {female_count}")
        print(f"  Средний возраст: {avg_age:.1f}")

        occupations = defaultdict(int)
        for u in self.users.values():
            occupations[u["occupation"]] += 1

        print(f"\nРод занятий:")
        for occ, count in sorted(occupations.items(), key=lambda x: x[1], reverse=True):
            print(f"  {occ}: {count}")

        input("\nНажмите Enter для продолжения...")

    def show_user_stats(self):
        """Subjects stats"""
        print("\n" + "-" * 50)
        print("СТАТИСТИКА ПО ПОЛЬЗОВАТЕЛЯМ")
        print("-" * 50)

        user_stats = []
        for user_id, tasks in self.user_tasks.items():
            user_info = self.users.get(user_id, {})
            user_stats.append(
                {
                    "username": user_info.get("username", user_id),
                    "age": user_info.get("age", "N/A"),
                    "sex": user_info.get("sex", "N/A"),
                    "occupation": user_info.get("occupation", "N/A"),
                    "task_count": len(tasks),
                    "total_time": timestamp_difference(
                        user_info.get("start_timestamp", "N/A"),
                        user_info.get("end_timestamp", "N/A"),
                    ),
                }
            )

        user_stats.sort(key=lambda x: x["task_count"], reverse=True)

        print(
            f"\n{'№':<3} {'Пользователь':<20} {'Возраст':<6} {'Пол':<4} {'Заданий':<8} {'Род занятий':<20} {'Общее время, сек'}"
        )
        print("-" * 70)

        for i, stats in enumerate(user_stats, 1):
            print(
                f"{i:<3} {stats['username']:<20} {stats['age']:<6} {stats['sex']:<4} {stats['task_count']:<8} {stats['occupation']:<20} {stats['total_time']}"
            )

        input("\nНажмите Enter для продолжения...")

    def show_task_stats(
        self, create_json: bool = True, output_path: str = "data/tasks.json"
    ):
        """Problems stats"""
        print("\n" + "-" * 50)
        print("СТАТИСТИКА ПО ЗАДАНИЯМ")
        print("-" * 50)

        task_stats: list[dict[str, str | int | float]] = []
        for image_name, responses in self.evaluations.items():
            sum_time = 0
            for response in responses.values():
                sum_time += response["time"]
            mean_time = sum_time / len(responses)

            correct = calc_correct_task(self.evaluations[image_name])
            task_stats.append(
                {
                    "image": image_name,
                    "response_count": len(responses),
                    "mean_time": mean_time,
                    "correct": correct,
                }
            )
        task_stats.sort(
            key=lambda x: x["response_count"], reverse=True
        )  # Sorting tasks stats
        numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        counts = [0] * 20

        if create_json:
            task_list = []
            for task in task_stats:
                for i in numbers:
                    if task["response_count"] == i:
                        counts[i] += 1
                new_task = {"name": task["image"][:-4], "used": task["response_count"]}
                task_list.append(new_task)
            data_json = {"tasks": task_list}
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data_json, f, ensure_ascii=False, indent=2)
        for i, co in enumerate(counts):
            print(f"{i}: {co}")
        print(
            f"\n{'№':<3} {'Изображение':<15} {'Кол-во ответов':<15} {'Верно':<10} {'Среднее время, сек'}"
        )
        print("-" * 50)

        for i, stats in enumerate(task_stats, 1):
            print(
                f"{i:<3} {stats['image']:<15} {stats['response_count']:<15} {stats['correct']:<10.1%} {stats['mean_time']:.1f}"
            )

        print("\nХотите посмотреть ответы на конкретное изображение?")
        choice = input(
            "Введите номер изображения из списка (или 'n' для выхода): "
        ).strip()

        if choice.lower() != "n":
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(task_stats):
                    selected_image = task_stats[idx]["image"]
                    print(f"\nОтветы на изображение '{selected_image}':")
                    print("-" * 50)

                    responses = self.evaluations[selected_image]
                    for i, resp in enumerate(responses.values(), 1):
                        print(
                            f"{i}. {resp['username']}: {resp['left_answer']} / {resp['right_answer']}"
                        )

                    # Опция открыть изображение
                    open_choice = (
                        input("\nОткрыть это изображение? (y/n): ").strip().lower()
                    )
                    if open_choice == "y":
                        self.show_image(selected_image)
                else:
                    print("Неверный номер")
            except ValueError:
                print("Неверный ввод")

        input("\nНажмите Enter для продолжения...")

    def evaluate_task(self, task_id: str, mode: Literal["all", "unrated", "unclear"]):

        print("\n" + "=" * 60)
        print(f"ПРОВЕРКА ЗАДАЧ")
        print("=" * 60)
        print(f"Задача {task_id}")
        self.show_image(task_id)
        task = deepcopy(self.evaluations[task_id])

        for user_id in task:
            answer = task[user_id]
            if (
                (mode == "unclear" and answer["evaluation"] not in ["", "y", "n"])
                or (mode == "unrated" and answer["evaluation"] == "")
                or mode == "all"
            ):
                print(f"\nОтветы {user_id}:")
                print({answer["left_answer"]})
                print({answer["right_answer"]})
                if answer["evaluation"] == "":
                    print(
                        "Оценки нет, введите 'y' если ответ верный, 'n' если неверный"
                    )
                else:
                    print(f"Сохраненная оценка: {answer['evaluation']}")
                    print(
                        "Введите 'y' если ответ верный, 'n' если неверный или нажмите Enter чтобы оставить старую оценку"
                    )
                eval = input(f"Оценка:").strip()
                if eval:
                    self.evaluations[task_id][user_id]["evaluation"] = eval
        with open(self.evaluation_path, "w", encoding="utf-8") as f:
            json.dump(self.evaluations, f, ensure_ascii=False, indent=2)

    def evaluations_menu(self):
        images = sorted(self.evaluations.keys())
        if not images:
            print("Нет данных об ответах на изображения!")
            return
        mode: Literal["all", "unrated", "unclear"] = "all"
        while True:
            sorted_eval = self._filter_evaluations(mode)

            task_keys = list(sorted_eval.keys())
            print("\nСписок задач")
            for i, task in enumerate(task_keys):
                print(f"{i+1}.  {task}")

            while True:
                try:
                    print(
                        f"\nВыбранный режим: {mode}. 'all' - Все задачи; 'unrated' - Не оцененные задачи; 'unclear' - Неоднозначные ответы; 'q' - выход"
                    )
                    choice = input(
                        f"Выберите задачу (1-{len(task_keys)}) или режим: "
                    ).strip()
                    if choice.lower() == "q":
                        return
                    elif choice.lower() == "all":
                        mode = "all"
                        break
                    elif choice.lower() == "unclear":
                        mode = "unclear"
                        break
                    elif choice.lower() == "unrated":
                        mode = "unrated"
                        break
                    idx = int(choice) - 1
                    if 0 <= idx < len(task_keys):
                        selected_task = task_keys[idx]
                        self.evaluate_task(selected_task, mode)
                        break
                    else:
                        print(f"Пожалуйста, выберите число от 1 до {len(task_keys)}")
                except ValueError:
                    print("Пожалуйста, введите корректное число")

    def main_menu(self):
        """Initial menu"""
        while True:
            print("\n" + "=" * 60)
            print("ПРОСМОТР РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
            print("=" * 60)
            print("\n1. Показать изображение и все ответы на него")
            print("2. Показать все ответы конкретного пользователя")
            print("3. Статистика")
            print("4. Проверка задач")
            print("5. Выход")

            choice = input("\nВыберите пункт меню (1-4): ").strip()

            if choice == "1":
                self.show_image_with_responses()
            elif choice == "2":
                self.show_user_images_and_responses()
            elif choice == "3":
                self.statistics_menu()
            elif choice == "4":
                self.evaluations_menu()
            elif choice == "5":
                print("\nДо свидания!")
                break
            else:
                print("Пожалуйста, выберите пункт от 1 до 5")

    def _filter_evaluations(self, mode: Literal["all", "unrated", "unclear"]):
        """Returns evaluations only across"""
        if mode == "all":
            return deepcopy(self.evaluations)

        if mode == "unrated":
            check = lambda e: e == ""
        elif mode == "unclear":
            check = lambda e: e not in {"", "y", "n"}
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return {
            p: deepcopy(evals)
            for p, evals in self.evaluations.items()
            if any(check(u["evaluation"]) for u in evals.values())
        }


def calc_correct_task(
    response: Dict[str, Dict[str, str]],
) -> float:  # correct answers percentage for one task
    ans_yes, ans_no, ans_other = 0, 0, 0
    for user in response.values():
        if user["evaluation"] == "y":
            ans_yes += 1
        elif user["evaluation"] == "n":
            ans_no += 1
        elif user["evaluation"] == "":
            pass
        else:
            ans_other += 1
    answers = ans_yes + ans_no + ans_other
    if answers == 0:
        correct = 0
    else:
        correct: float = ans_yes / answers
    return correct


def main():
    """Основная функция"""
    print("=" * 60)
    print("ЗАГРУЗКА ПРОГРАММЫ")
    print("=" * 60)

    # Получение путей от пользователя
    json_path = Path(...)
    images_folder = Path(...)
    evaluation_path = Path(...)  # Could not exist

    # Создаем и запускаем приложение
    app = TestResultsViewer(json_path, images_folder, evaluation_path)
    app.main_menu()


if __name__ == "__main__":
    main()
