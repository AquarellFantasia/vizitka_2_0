"""Database for anime favorites and episode tracking."""

import csv
import json
import os
from pathlib import Path


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


class Database:
    """Stores favorite anime list and registered episodes."""

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir or os.getenv("ANIME_DB_PATH", _default_data_dir()))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._favorites_path = self.data_dir / "favorites.json"
        self._csv_path = self.data_dir / "anime_db.csv"
        self._df = self._load_csv()
        self._favorites = self._load_favorites()

    def _load_csv(self) -> list[dict]:
        if self._csv_path.exists():
            with open(self._csv_path, encoding="utf-8", newline="") as f:
                return list(csv.DictReader(f))
        return []

    def _load_favorites(self) -> list[str]:
        if self._favorites_path.exists():
            with open(self._favorites_path, encoding="utf-8") as f:
                return json.load(f)
        return self._default_favorites()

    def _default_favorites(self) -> list[str]:
        return [
            "Герой-рационал",
            "фарфоровая кукла",
            "Магическая битва",
            "Рейтинг короля",
            "Арифурэта",
            "Повелитель",
            "Реинкарнация безработного",
            "Ванпанчмен",
            "Блич",
            "Восхождение героя щита",
            "Haikyuu",
            "О моём перерождении в слизь",
            "Мастера меча онлайн",
            "Жизнь в альтернативном мире с нуля",
            "Убийца гоблинов",
            "Вторжение Гигантов",
            "Повесть о конце света",
            "Доктор Стоун",
            "Месть Масамунэ",
            "Непутёвый ученик в школе магии",
            "Маг на полную ставку",
            "Этот замечательный мир",
            "Моб Психо 100",
            "Сага о Винланде",
            "Ох, уж этот экстрасенс Сайки Кусуо",
            "Башня Бога",
            "Князь тьмы меняет профессию",
            "Пламенная бригада пожарных",
            "Добро пожаловать в ад, Ирума",
            "Госпожа Кагуя",
            "24 округ Токио",
            "Токийские мстители",
            "Сбережение восьмидесяти тысяч золотых монет",
            "Для тебя, Бессмертный",
            "Перевоплотившийся король-герой",
        ]

    def _save_csv(self) -> None:
        with open(self._csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Full name", "Last episode"])
            writer.writeheader()
            writer.writerows(self._df)

    def _save_favorites(self) -> None:
        with open(self._favorites_path, "w", encoding="utf-8") as f:
            json.dump(self._favorites, f, ensure_ascii=False, indent=2)

    @property
    def favorites(self) -> list[str]:
        return self._favorites.copy()

    def set_favorites(self, titles: list[str]) -> None:
        self._favorites = [t.strip() for t in titles if t.strip()]
        self._save_favorites()

    def add_favorite(self, title: str) -> None:
        t = title.strip()
        if t and t not in self._favorites:
            self._favorites.append(t)
            self._save_favorites()

    def remove_favorite(self, title: str) -> None:
        if title in self._favorites:
            self._favorites.remove(title)
            self._save_favorites()

    def is_episode_registered(self, full_name: str, episode: str) -> bool:
        for row in self._df:
            if row["Full name"] == full_name:
                return row["Last episode"] == episode
        return False

    def add_anime(self, full_name: str, last_episode: str) -> None:
        self._df.insert(0, {"Full name": full_name, "Last episode": last_episode})
        self._save_csv()

    def update_episode(self, full_name: str, last_episode: str) -> None:
        for row in self._df:
            if row["Full name"] == full_name:
                row["Last episode"] = last_episode
                self._save_csv()
                return

    def get_registered(self, full_name: str) -> str | None:
        for row in self._df:
            if row["Full name"] == full_name:
                return row["Last episode"]
        return None
