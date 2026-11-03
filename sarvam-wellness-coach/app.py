import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

# UTF-8 terminal output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from voice_pipeline import VoicePipeline
from coach_engine import CoachEngine

def print_banner():
    print("""
========================================================================
    🎙️  AURA • VOICE-FIRST WELLNESS & NUTRITION COMPANION
       (Adaptive Indian Nutrition, Workouts & Recovery Engine)
========================================================================
""")

def print_dashboard(today: dict, profile: dict, adaptive_action: str = ""):
    totals = today.get("totals", {})
    cals = totals.get("calories", 0)
    prot = totals.get("protein_g", 0)
    carbs = totals.get("carbs_g", 0)
    fat = totals.get("fat_g", 0)

    c_target = profile.get("calorie_target", 2100)
    p_target = profile.get("protein_target_g", 120)
    carb_target = profile.get("carbs_target_g", 220)
    f_target = profile.get("fat_target_g", 60)

    workout = today.get("workout", {})
    sleep = today.get("sleep", {})
    energy = today.get("energy_level", "unknown")
    streak = profile.get("workout_streak_days", 0)

    print("\n" + "-"*60)
    print(" 📊 LIVE WELLNESS DASHBOARD (TODAY)")
    print("-" * 60)
    print(f" 🔥 Calories : {cals:4d} / {c_target} kcal  [{'='*min(20, int(cals/c_target*20)):<20}]")
    print(f" 🥩 Protein  : {prot:4d} / {p_target} g     [{'='*min(20, int(prot/p_target*20)):<20}]")
    print(f" 🍚 Carbs    : {carbs:4d} / {carb_target} g     [{'='*min(20, int(carbs/carb_target*20)):<20}]")
    print(f" 🥑 Fats     : {fat:4d} / {f_target} g     [{'='*min(20, int(fat/f_target*20)):<20}]")
    print("-" * 60)
    print(f" 🏃 Workout  : {workout.get('activity', 'None')} ({workout.get('duration_min', 0)} min) - [{workout.get('status', 'none').upper()}]")
    print(f" 🔥 Streak   : {streak} Days")
    print(f" 😴 Sleep    : {sleep.get('hours', 0.0)} hrs (Quality: {sleep.get('quality_1_to_5', '-')}/5)")
    print(f" ⚡ Energy   : {energy.upper()}")
    
    if adaptive_action:
        print(f" 🎯 Adaptive : {adaptive_action}")
    elif today.get("adaptive_actions"):
        print(f" 🎯 Adaptive : {today['adaptive_actions'][-1]}")

    meals = today.get("meals", [])
    if meals:
        print("\n 🍲 Logged Meals Today:")
        for idx, m in enumerate(meals, 1):
            print(f"    {idx}. {m.get('item', 'Meal')}: {m.get('calories', 0)} kcal | P:{m.get('protein_g',0)}g C:{m.get('carbs_g',0)}g F:{m.get('fat_g',0)}g")
    print("-" * 60 + "\n")

def run_turn(pipeline: VoicePipeline, engine: CoachEngine, user_text: str, mode: str = "general", audio_file: str = None):
    print(f"\n[Coach is thinking & analyzing nutrition/state...]")

    audio_bytes = None
    if audio_file and os.path.exists(audio_file):
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

    recent_history = engine.get_recent_3_days()
    result = pipeline.process_turn(
        user_text=user_text,
        audio_bytes=audio_bytes,
        audio_filename=audio_file or "input.wav",
        recent_history=recent_history,
        checkin_mode=mode,
        save_tts_path="latest_coach_reply.wav"
    )

    coach_data = result["coach_data"]
    log_update = coach_data.get("log_update", {})
    adaptive_action = coach_data.get("adaptive_action", "")

    # Apply updates
    engine.apply_log_update(log_update, adaptive_action)

    print("\n" + "="*60)
    if result["user_transcript"]:
        print(f"👤 You (Transcribed): \"{result['user_transcript']}\"")
    print(f"🎙️ Aura Coach Voice: \"{result['spoken_reply']}\"")
    print(f"🔊 Audio Output saved to: {result['audio_path']}")
    print("=" * 60)

    print_dashboard(engine.get_today(), engine.get_profile(), adaptive_action)

def main():
    parser = argparse.ArgumentParser(description="Sarvam AI Wellness Coach")
    parser.add_argument("--browser", action="store_true", help="Launch interactive browser dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Port for web dashboard")
    args = parser.parse_args()

    if args.browser:
        from server import run_server
        run_server(port=args.port, auto_open=True)
        return

    print_banner()
    pipeline = VoicePipeline()
    engine = CoachEngine()

    print_dashboard(engine.get_today(), engine.get_profile())

    while True:
        print("""
Choose an action:
  1. 🌅 Morning Check-In (Sleep & Daily Goals)
  2. ☀️ Midday Nudge (Lunch & Hydration)
  3. ⚠️ Missed Workout Follow-Up
  4. 🌙 Evening Wrap-Up (Dinner, Day Review & Sleep Tip)
  5. 💬 Free-form Check-In (Type or code-mixed Indian meal description)
  6. 🌐 Launch in External Browser
  0. Exit
""")
        choice = input("Enter choice (0-6): ").strip()

        if choice == "1":
            nudge = engine.get_proactive_nudge("morning_checkin")
            print(f"\n🎙️ Coach: {nudge['initial_prompt']}")
            user_in = input("\nYour response (e.g., 'Slept 7 hours, feeling fresh, ready for leg day'): ")
            if user_in.strip():
                run_turn(pipeline, engine, user_in, mode="morning_checkin")

        elif choice == "2":
            nudge = engine.get_proactive_nudge("midday_nudge")
            print(f"\n🎙️ Coach: {nudge['initial_prompt']}")
            user_in = input("\nYour response (e.g., 'Had 2 rotis with paneer bhurji and a katori of dal'): ")
            if user_in.strip():
                run_turn(pipeline, engine, user_in, mode="midday_nudge")

        elif choice == "3":
            print("\n🎙️ Coach: Hey, I noticed today's scheduled workout was missed. How are your energy levels?")
            user_in = input("\nYour response (e.g., 'Work was hectic and only had 5 hours sleep, skipped it'): ")
            if user_in.strip():
                run_turn(pipeline, engine, user_in, mode="missed_workout")

        elif choice == "4":
            nudge = engine.get_proactive_nudge("evening_wrapup")
            print(f"\n🎙️ Coach: {nudge['initial_prompt']}")
            user_in = input("\nYour response (e.g., 'Had light khichdi with curd and 1 papad'): ")
            if user_in.strip():
                run_turn(pipeline, engine, user_in, mode="evening_wrapup")

        elif choice == "5":
            user_in = input("\nEnter meal, workout or sleep update: ")
            if user_in.strip():
                run_turn(pipeline, engine, user_in, mode="general")

        elif choice == "6":
            from server import run_server
            run_server(port=args.port, auto_open=True)
            break

        elif choice == "0":
            print("Exiting. Keep thriving!")
            break

if __name__ == "__main__":
    main()
