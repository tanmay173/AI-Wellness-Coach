import os
import sys
import json
import base64
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from voice_pipeline import VoicePipeline
from coach_engine import CoachEngine

# Ensure UTF-8 output in Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8080
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
pipeline = None
engine = None

class WellnessHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            html_file = os.path.join(WORKSPACE_DIR, "index.html")
            if os.path.exists(html_file):
                with open(html_file, "rb") as f:
                    content_bytes = f.read()
            else:
                content_bytes = b"<h1>index.html not found</h1>"

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content_bytes)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(content_bytes)

        elif parsed.path == "/api/state":
            state = {
                "profile": engine.get_profile(),
                "today": engine.get_today(),
                "history": engine.get_recent_3_days()
            }
            self.send_json(state, 200)

        elif parsed.path.endswith((".png", ".jpg", ".jpeg", ".svg", ".ico", ".wav")):
            rel_path = parsed.path.lstrip("/")
            file_on_disk = os.path.join(WORKSPACE_DIR, rel_path)
            if os.path.exists(file_on_disk):
                content_type = "image/png" if rel_path.endswith(".png") else "audio/wav" if rel_path.endswith(".wav") else "application/octet-stream"
                with open(file_on_disk, "rb") as f:
                    file_bytes = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(file_bytes)))
                self.end_headers()
                self.wfile.write(file_bytes)
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if parsed.path == "/api/interact":
            try:
                user_text = payload.get("text")
                audio_b64 = payload.get("audio_base64")
                filename = payload.get("filename", "input.webm")
                mode = payload.get("mode")
                speaker = payload.get("speaker") or engine.get_profile().get("selected_voice", "simran")
                voice_id = payload.get("voice_id")
                portion_mult = float(payload.get("portion_mult") or engine.get_profile().get("portion_size_multiplier", 1.0))
                voice_pace = float(payload.get("voice_pace") or 0.95)

                audio_bytes = base64.b64decode(audio_b64) if audio_b64 else None
                recent_history = engine.get_recent_3_days()

                turn_result = pipeline.process_turn(
                    user_text=user_text,
                    audio_bytes=audio_bytes,
                    audio_filename=filename,
                    recent_history=recent_history,
                    checkin_mode=mode,
                    speaker=speaker,
                    voice_id=voice_id,
                    portion_mult=portion_mult,
                    voice_pace=voice_pace,
                    save_tts_path=os.path.join(WORKSPACE_DIR, "latest_coach_reply.wav")
                )

                coach_data = turn_result["coach_data"]
                log_update = coach_data.get("log_update", {})
                adaptive_action = coach_data.get("adaptive_action", "")
                engine.apply_log_update(log_update, adaptive_action)

                response_payload = {
                    "user_transcript": turn_result["user_transcript"],
                    "spoken_reply": turn_result["spoken_reply"],
                    "audio_base64": turn_result["audio_base64"],
                    "coach_data": coach_data,
                    "today": engine.get_today(),
                    "profile": engine.get_profile()
                }

                self.send_json(response_payload, 200)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif parsed.path == "/api/nudge":
            try:
                mode = payload.get("mode", "morning_checkin")
                speaker = payload.get("speaker") or engine.get_profile().get("selected_voice", "simran")
                voice_id = payload.get("voice_id")
                voice_pace = float(payload.get("voice_pace") or 0.95)

                nudge = engine.get_proactive_nudge(mode)
                prompt_text = nudge["initial_prompt"]

                audio_bytes, _ = pipeline.text_to_speech(
                    text=prompt_text,
                    language_code="hi-IN",
                    speaker=speaker,
                    voice_id=voice_id,
                    pace=voice_pace
                )
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

                res = {
                    "mode": mode,
                    "title": nudge["title"],
                    "initial_prompt": prompt_text,
                    "audio_base64": audio_b64
                }

                self.send_json(res, 200)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif parsed.path == "/api/profile":
            try:
                new_profile = payload.get("profile", {})
                updated = engine.update_profile(new_profile)
                self.send_json({"profile": updated}, 200)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif parsed.path == "/api/clone-voice":
            try:
                name = payload.get("name", "Custom Voice")
                gender = payload.get("gender", "female")
                sample_b64 = payload.get("sample_audio_base64")
                
                voice_entry = {
                    "voice_id": f"cloned_{len(engine.get_profile().get('cloned_voices', []))+1}",
                    "name": name,
                    "gender": gender
                }

                if sample_b64:
                    raw_audio = base64.b64decode(sample_b64)
                    try:
                        voice_resp = pipeline.clone_voice(raw_audio, name, gender)
                        voice_entry["voice_id"] = voice_resp.get("voice_id", voice_entry["voice_id"])
                    except Exception as err:
                        # Fallback: save voice sample locally for zero-shot or mock clone
                        sample_path = os.path.join(WORKSPACE_DIR, f"{voice_entry['voice_id']}.wav")
                        with open(sample_path, "wb") as f:
                            f.write(raw_audio)
                        voice_entry["sample_path"] = sample_path

                all_cloned = engine.add_cloned_voice(voice_entry)
                engine.update_profile({"selected_voice": voice_entry["voice_id"]})

                self.send_json({"success": True, "voice": voice_entry, "cloned_voices": all_cloned}, 200)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif parsed.path == "/api/reset":
            try:
                today = engine.reset_today()
                res = {
                    "today": today,
                    "profile": engine.get_profile()
                }
                self.send_json(res, 200)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port: int = PORT, auto_open: bool = True):
    global pipeline, engine
    pipeline = VoicePipeline()
    engine = CoachEngine()

    server_address = ("", port)
    try:
        httpd = HTTPServer(server_address, WellnessHandler)
    except OSError:
        port = port + 1
        server_address = ("", port)
        httpd = HTTPServer(server_address, WellnessHandler)

    url = f"http://localhost:{port}"
    print(f"\n========================================================")
    print(f"  🎙️ Voice First AI Wellness Coach Web Server Started!")
    print(f"  👉 URL: {url}")
    print(f"  Live UI: {os.path.join(WORKSPACE_DIR, 'index.html')}")
    print(f"========================================================\n")

    if auto_open:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    auto = "--no-browser" not in sys.argv
    run_server(PORT, auto_open=auto)
