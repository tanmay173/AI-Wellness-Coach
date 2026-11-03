import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

LOG_FILE = "wellness_logs.json"

DEFAULT_DATA = {
    "user_profile": {
        "name": "User",
        "calorie_target": 2100,
        "protein_target_g": 120,
        "carbs_target_g": 220,
        "fat_target_g": 60,
        "fiber_target_g": 32,
        "water_target_l": 3.0,
        "portion_size_multiplier": 1.0,
        "workout_streak_days": 6,
        "selected_voice": "simran",
        "cloned_voices": []
    },
    "history": [
        {
            "date": (date.today() - timedelta(days=2)).isoformat(),
            "meals": [
                {"item": "2 Besan Chilla + green chutney", "calories": 320, "protein_g": 16, "carbs_g": 38, "fat_g": 10, "fiber_g": 6},
                {"item": "Rajma Chawal + cucumber salad", "calories": 580, "protein_g": 22, "carbs_g": 85, "fat_g": 14, "fiber_g": 12},
                {"item": "Paneer bhurji with 2 multigrain rotis", "calories": 610, "protein_g": 34, "carbs_g": 48, "fat_g": 28, "fiber_g": 8}
            ],
            "workout": {"activity": "HIIT & Core", "duration_min": 40, "status": "completed"},
            "sleep": {"hours": 7.5, "quality_1_to_5": 4},
            "energy_level": "high",
            "totals": {"calories": 1510, "protein_g": 72, "carbs_g": 171, "fat_g": 52, "fiber_g": 26, "water_liters": 2.8}
        },
        {
            "date": (date.today() - timedelta(days=1)).isoformat(),
            "meals": [
                {"item": "Poha with roasted peanuts + tea", "calories": 360, "protein_g": 10, "carbs_g": 56, "fat_g": 11, "fiber_g": 5},
                {"item": "Dal Tadka, 2 rotis, curd", "calories": 520, "protein_g": 20, "carbs_g": 72, "fat_g": 15, "fiber_g": 8},
                {"item": "Grilled soya chunks with stir fry veggies", "calories": 480, "protein_g": 42, "carbs_g": 30, "fat_g": 12, "fiber_g": 10}
            ],
            "workout": {"activity": "Upper Body Strength", "duration_min": 45, "status": "completed"},
            "sleep": {"hours": 6.8, "quality_1_to_5": 3},
            "energy_level": "moderate",
            "totals": {"calories": 1360, "protein_g": 72, "carbs_g": 158, "fat_g": 38, "fiber_g": 23, "water_liters": 2.5}
        }
    ],
    "today": {
        "date": date.today().isoformat(),
        "meals": [],
        "workout": {"activity": "Strength & Core", "duration_min": 45, "status": "planned"},
        "sleep": {"hours": 0.0, "quality_1_to_5": 0},
        "energy_level": "unknown",
        "adaptive_actions": [],
        "totals": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0, "water_liters": 0.0}
    }
}

class CoachEngine:
    def __init__(self, filepath: str = LOG_FILE):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    today_str = date.today().isoformat()
                    if data.get("today", {}).get("date") != today_str:
                        if data.get("today"):
                            data.setdefault("history", []).append(data["today"])
                        data["today"] = {
                            "date": today_str,
                            "meals": [],
                            "workout": {"activity": "Strength & Core", "duration_min": 45, "status": "planned"},
                            "sleep": {"hours": 0.0, "quality_1_to_5": 0},
                            "energy_level": "unknown",
                            "adaptive_actions": [],
                            "totals": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0, "water_liters": 0.0}
                        }
                    # Ensure new keys exist in profile
                    prof = data.setdefault("user_profile", {})
                    prof.setdefault("fiber_target_g", 32)
                    prof.setdefault("water_target_l", 3.0)
                    prof.setdefault("portion_size_multiplier", 1.0)
                    prof.setdefault("selected_voice", "aditya")
                    prof.setdefault("cloned_voices", [])
                    # Ensure totals have new keys
                    tot = data.setdefault("today", {}).setdefault("totals", {})
                    tot.setdefault("fiber_g", 0)
                    tot.setdefault("water_liters", 0.0)
                    return data
            except Exception:
                pass
        
        self._save(DEFAULT_DATA)
        return DEFAULT_DATA

    def _save(self, data: Optional[Dict[str, Any]] = None):
        if data is None:
            data = self.data
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_recent_3_days(self) -> List[Dict[str, Any]]:
        history = list(self.data.get("history", []))
        history.append(self.data.get("today", {}))
        return history[-3:]

    def get_today(self) -> Dict[str, Any]:
        return self.data.get("today", {})

    def get_profile(self) -> Dict[str, Any]:
        return self.data.get("user_profile", {})

    def update_profile(self, new_profile: Dict[str, Any]) -> Dict[str, Any]:
        prof = self.data.setdefault("user_profile", {})
        for k, v in new_profile.items():
            prof[k] = v
        self._save()
        return prof

    def add_cloned_voice(self, voice_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        cloned = self.data.setdefault("user_profile", {}).setdefault("cloned_voices", [])
        # Check if already exists
        exists = False
        for v in cloned:
            if v.get("name") == voice_info.get("name"):
                v.update(voice_info)
                exists = True
                break
        if not exists:
            cloned.append(voice_info)
        self._save()
        return cloned

    def apply_log_update(self, log_update: Dict[str, Any], adaptive_action: Optional[str] = None):
        today = self.data["today"]

        # Meals
        meals = log_update.get("meals", [])
        if isinstance(meals, list):
            for m in meals:
                if isinstance(m, dict) and m.get("item"):
                    m.setdefault("fiber_g", max(1, int(m.get("carbs_g", 0) * 0.12)))
                    today["meals"].append(m)

        # Hydration
        water = log_update.get("hydration_liters", 0.0)
        if water and water > 0:
            today["totals"]["water_liters"] = round(today["totals"].get("water_liters", 0.0) + float(water), 1)

        # Workouts
        workout = log_update.get("workout")
        if isinstance(workout, dict) and workout.get("activity"):
            today["workout"] = {
                "activity": workout.get("activity", today["workout"].get("activity", "")),
                "duration_min": workout.get("duration_min", today["workout"].get("duration_min", 0)),
                "status": workout.get("status", today["workout"].get("status", "completed"))
            }
            if workout.get("status") == "completed":
                self.data["user_profile"]["workout_streak_days"] += 1

        # Sleep
        sleep = log_update.get("sleep")
        if isinstance(sleep, dict):
            if sleep.get("hours", 0) > 0:
                today["sleep"]["hours"] = float(sleep.get("hours", 0))
            if sleep.get("quality_1_to_5", 0) > 0:
                today["sleep"]["quality_1_to_5"] = int(sleep.get("quality_1_to_5", 0))

        # Energy Level
        energy = log_update.get("energy_level")
        if energy and energy != "unknown":
            today["energy_level"] = energy

        # Adaptive Action
        if adaptive_action and adaptive_action.strip():
            today["adaptive_actions"].append(adaptive_action.strip())

        # Recalculate totals
        cals = sum(m.get("calories", 0) for m in today["meals"])
        prot = sum(m.get("protein_g", 0) for m in today["meals"])
        carbs = sum(m.get("carbs_g", 0) for m in today["meals"])
        fat = sum(m.get("fat_g", 0) for m in today["meals"])
        fiber = sum(m.get("fiber_g", 0) for m in today["meals"])

        today["totals"]["calories"] = cals
        today["totals"]["protein_g"] = prot
        today["totals"]["carbs_g"] = carbs
        today["totals"]["fat_g"] = fat
        today["totals"]["fiber_g"] = fiber

        self._save()

    def reset_today(self) -> Dict[str, Any]:
        today_str = date.today().isoformat()
        self.data["today"] = {
            "date": today_str,
            "meals": [],
            "workout": {"activity": "Strength & Core", "duration_min": 45, "status": "planned"},
            "sleep": {"hours": 0.0, "quality_1_to_5": 0},
            "energy_level": "unknown",
            "adaptive_actions": [],
            "totals": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0, "water_liters": 0.0}
        }
        self._save()
        return self.data["today"]

    def get_proactive_nudge(self, mode: str) -> Dict[str, str]:
        today = self.get_today()
        profile = self.get_profile()

        if mode == "morning_checkin":
            return {
                "mode": "morning_checkin",
                "title": "Morning Check-In",
                "initial_prompt": "Suprabhat! Raat ko neend kaisi rahi, aur aaj subah kaisa mehsoos ho raha hai? Chaliye aaj ka din ek calm aur positive note pe shuru karte hain!",
                "description": "Reviews last night's sleep, morning energy, and sets daily goals."
            }
        elif mode == "midday_nudge":
            workout_status = today.get("workout", {}).get("status", "planned")
            if workout_status == "skipped":
                initial = "Namaste! Agar subah ka workout miss ho gaya, toh bilkul chinta mat kijiye. Rest bhi recovery ka part hai. Aaj lunch kaisa raha, aur din bhar hydration ka dhyan raha?"
            else:
                initial = "Namaste! Aaj lunch kaisa raha? Aur kya din bhar paani peene ka dhyan raha? Aaiye aaj ka nutrition sync kar lete hain."
            return {
                "mode": "midday_nudge",
                "title": "Midday Nutrition & Workout Nudge",
                "initial_prompt": initial,
                "description": "Checks lunch intake, hydration, and adapts missed workout plans."
            }
        elif mode == "evening_wrapup":
            initial = "Good evening! Aaj dinner mein kya khaya? Aaiye aaj ka din sync karte hain, thoda relax kijiye taaki raat ko shaant neend aaye."
            return {
                "mode": "evening_wrapup",
                "title": "Evening Nutrition & Sleep Wrap-Up",
                "initial_prompt": initial,
                "description": "Summarizes daily macros vs targets and provides sleep-hygiene recommendations."
            }
        else:
            return {
                "mode": "general",
                "title": "General Health Check-In",
                "initial_prompt": "Namaste! Main aapka AI Wellness Coach hoon. Aaj apne meals, workout ya neend ke baare mein kya share karna chahenge?",
                "description": "Open-ended wellness conversation."
            }
