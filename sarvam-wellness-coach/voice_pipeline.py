import os
import json
import base64
import io
import re
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

SYSTEM_PROMPT = """You are a warm, perceptive AI Wellness Coach built for Indian users. You conduct brief, natural voice check-ins to track food intake, workouts, hydration, and sleep without making the user feel like they are filling out a form.

Core Behaviors:
1. Soothing & Non-Irritating Voice Tone: The `spoken_reply` field will be spoken aloud to the user over audio. Make it sound like a caring, encouraging personal friend or yoga instructor. Keep it short (1 to 2 warm, natural sentences, under 30 words). NEVER list raw numbers, exact calorie counts, grams of protein, or percentages in the spoken audio (those are already shown on the screen). Speak conversationally, empathetically, and soothingly (e.g. "Bahut badhiya lunch tha! Dal aur paneer se body ko acchi strength milegi. Din bhar hydration ka zaroor dhyan rakhiyega.").
2. Code-Mixed Natural Fluency: Mirror the user's language naturally (Hinglish, English, Hindi, or other Indian languages) with a soft, friendly cadence without robotic or clinical jargon.
3. Effortless Indian Nutrition Estimation: When the user mentions food (e.g., "had 2 idlis with sambar and filter coffee" or "lunch mein dal chawal aur paneer bhurji khaya"), automatically estimate realistic portion calories, macronutrients (protein, carbs, fats) and dietary fiber in the background without interrogating them for exact gram weights. If the user mentions water or hydration, estimate hydration_liters.
4. Adaptive & Empathetic Coaching: If the user missed a workout or slept poorly, never guilt-trip them. Validate their energy level gently (e.g., "Koi baat nahi, rest lena bhi recovery ka part hai. Aaj bas 10-15 minute halki walk ya stretch kar lijiye.").
5. Holistic Trend Awareness: Connect sleep quality, hydration, and protein intake to their workout recovery and afternoon energy levels.

Always respond in strictly valid JSON matching this schema:
{
  "spoken_reply": "Warm, conversational voice response to be spoken via TTS (1-2 sentences, under 30 words, zero numbers/grams)",
  "detected_language_code": "hi-IN or en-IN etc.",
  "log_update": {
    "meals": [
      {"item": "string", "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0}
    ],
    "hydration_liters": 0.0,
    "workout": {
      "activity": "string",
      "duration_min": 0,
      "status": "completed | skipped | modified | planned | none"
    },
    "sleep": {
      "hours": 0.0,
      "quality_1_to_5": 0
    },
    "energy_level": "low | medium | high | unknown"
  },
  "adaptive_action": "Short note on how today's plan was adjusted based on user state"
}
"""

class VoicePipeline:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable not found.")
        self.client = SarvamAI(api_subscription_key=self.api_key)

    def speech_to_text(
        self,
        audio_input: Any,
        filename: str = "input.wav",
        language_code: str = "unknown"
    ) -> Dict[str, str]:
        """
        Transcribes speech using saaras:v3 ASR with Indian code-mix detection.
        """
        if isinstance(audio_input, (bytes, bytearray)):
            file_obj = (filename, io.BytesIO(audio_input))
        elif isinstance(audio_input, str):
            file_obj = open(audio_input, "rb")
        else:
            file_obj = audio_input

        try:
            resp = self.client.speech_to_text.transcribe(
                file=file_obj,
                model="saaras:v3",
                mode="codemix",
                language_code=language_code if language_code != "unknown" else None
            )
            return {
                "transcript": resp.transcript or "",
                "detected_language": resp.language_code or "hi-IN"
            }
        finally:
            if isinstance(audio_input, str) and hasattr(file_obj, "close"):
                file_obj.close()

    def coach_brain(
        self,
        user_message: str,
        recent_history: Optional[List[Dict[str, Any]]] = None,
        checkin_mode: Optional[str] = None,
        user_portion_mult: float = 1.0
    ) -> Dict[str, Any]:
        """
        Processes transcribed input and returns structured coaching response + health logs.
        """
        context_str = ""
        if recent_history:
            context_str = f"\nUser Recent 3-Day Health Context:\n{json.dumps(recent_history, indent=2)}\n"

        checkin_context = ""
        if checkin_mode:
            checkin_context = f"\nCurrent Active Check-In Mode: {checkin_mode}\n"

        portion_context = f"\nUser Portion Scaling Factor: {user_portion_mult}x (Scale estimated calories/macros accordingly)\n"

        prompt = f"""{context_str}{checkin_context}{portion_context}
User Input: "{user_message}"

Generate the JSON response following the instructions:"""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        response = self.client.chat.completions(
            model="sarvam-105b-conversations",
            messages=messages,
            max_tokens=700
        )

        content = response.choices[0].message.content or ""
        return self._extract_json(content)

    def text_to_speech(
        self,
        text: str,
        language_code: str = "hi-IN",
        speaker: str = "simran",
        voice_id: Optional[str] = None,
        ref_audio_bytes: Optional[bytes] = None,
        output_filename: Optional[str] = None,
        pace: float = 0.95,
        temperature: float = 0.35,
        speech_sample_rate: int = 24000
    ) -> Tuple[bytes, Optional[str]]:
        """
        Converts text to speech using soothing companion voices, fine-tuned cadence, and studio clarity.
        """
        valid_langs = ["hi-IN", "en-IN", "bn-IN", "gu-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"]
        lang = language_code if language_code in valid_langs else "hi-IN"

        clean_text = text.strip()
        if not clean_text:
            clean_text = "Main aapka wellness coach hoon."

        # If custom cloned voice_id or ref_audio is provided
        if voice_id or ref_audio_bytes:
            try:
                ref_file = ("ref.wav", io.BytesIO(ref_audio_bytes)) if ref_audio_bytes else None
                resp = self.client.voice_cloning.convert(
                    text=clean_text,
                    voice_id=voice_id,
                    ref_audio=ref_file,
                    language_code=lang,
                    output_audio_codec="wav"
                )
                if resp.audio_b64:
                    audio_bytes = base64.b64decode(resp.audio_b64)
                    if output_filename:
                        with open(output_filename, "wb") as f:
                            f.write(audio_bytes)
                    return audio_bytes, output_filename
            except Exception as e:
                # Graceful fallback to standard speaker if voice cloning fails
                pass

        # Smart Speaker & Model Mapping for soothing, non-irritating natural speech
        speaker_lower = (speaker or "simran").lower().strip()

        # Map speakers to the best model and persona
        if speaker_lower in ["simran", "anushka", "companion"]:
            target_speaker = "simran_enhi_companion"
            target_model = "bulbul:v4-flash"
        elif speaker_lower in ["shubh", "shubh_enhi"]:
            target_speaker = "shubh_enhi_companion"
            target_model = "bulbul:v4-flash"
        elif speaker_lower in ["kavya", "dev", "priya", "rohan", "aditya", "ashutosh", "ritu", "rahul", "pooja"]:
            target_speaker = speaker_lower
            target_model = "bulbul:v3"
        elif "_" in speaker_lower:
            target_speaker = speaker_lower
            target_model = "bulbul:v4-flash"
        else:
            target_speaker = "simran_enhi_companion"
            target_model = "bulbul:v4-flash"

        # Constrain pace to natural, pleasant conversational tempo (0.85 to 1.15)
        safe_pace = max(0.85, min(1.20, float(pace or 0.95)))
        safe_temp = max(0.20, min(0.50, float(temperature or 0.35)))

        try:
            resp = self.client.text_to_speech.convert(
                text=clean_text,
                language_code=lang,
                speaker=target_speaker,
                model=target_model,
                pace=safe_pace,
                temperature=safe_temp,
                speech_sample_rate=speech_sample_rate,
                output_audio_codec="wav"
            )
        except Exception as e:
            # Automatic graceful fallback to ultra-reliable bulbul:v3 kavya or simran
            try:
                resp = self.client.text_to_speech.convert(
                    text=clean_text,
                    language_code=lang,
                    speaker="kavya",
                    model="bulbul:v3",
                    pace=safe_pace,
                    temperature=safe_temp,
                    speech_sample_rate=speech_sample_rate,
                    output_audio_codec="wav"
                )
            except Exception as e2:
                resp = self.client.text_to_speech.convert(
                    text=clean_text,
                    language_code=lang,
                    speaker="aditya",
                    model="bulbul:v3",
                    pace=safe_pace,
                    output_audio_codec="wav"
                )

        if not resp.audios:
            raise RuntimeError("No audio returned from TTS service.")

        audio_bytes = base64.b64decode(resp.audios[0])
        if output_filename:
            with open(output_filename, "wb") as f:
                f.write(audio_bytes)

        return audio_bytes, output_filename

    def clone_voice(self, audio_bytes: bytes, name: str, gender: str = "female") -> Dict[str, Any]:
        """
        Creates a custom cloned voice model from audio sample.
        """
        file_obj = ("voice_sample.wav", io.BytesIO(audio_bytes))
        resp = self.client.voice_cloning.create_voice(
            file=file_obj,
            name=name,
            language="hi-IN",
            gender=gender,
            style="conversational"
        )
        voice_id = resp.data.voice_id if hasattr(resp, "data") and hasattr(resp.data, "voice_id") else name
        return {
            "voice_id": voice_id,
            "name": name,
            "gender": gender
        }

    def process_turn(
        self,
        user_text: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        audio_filename: str = "input.wav",
        recent_history: Optional[List[Dict[str, Any]]] = None,
        checkin_mode: Optional[str] = None,
        speaker: str = "simran",
        voice_id: Optional[str] = None,
        ref_audio_bytes: Optional[bytes] = None,
        portion_mult: float = 1.0,
        voice_pace: float = 0.95,
        save_tts_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs full pipeline: STT (if audio provided) -> LLM Coach Brain -> Voice Synthesis.
        """
        transcript = user_text or ""
        stt_lang = "hi-IN"

        if audio_bytes:
            stt_result = self.speech_to_text(audio_bytes, filename=audio_filename)
            transcript = stt_result["transcript"]
            stt_lang = stt_result.get("detected_language", "hi-IN")

        coach_data = self.coach_brain(transcript, recent_history, checkin_mode, user_portion_mult=portion_mult)
        spoken_reply = coach_data.get("spoken_reply", "Main aapki baat samajh gaya hoon.")
        target_lang = coach_data.get("detected_language_code") or stt_lang

        audio_bytes_out, saved_path = self.text_to_speech(
            text=spoken_reply,
            language_code=target_lang,
            speaker=speaker,
            voice_id=voice_id,
            ref_audio_bytes=ref_audio_bytes,
            output_filename=save_tts_path,
            pace=voice_pace
        )

        return {
            "user_transcript": transcript,
            "coach_data": coach_data,
            "spoken_reply": spoken_reply,
            "audio_bytes": audio_bytes_out,
            "audio_path": saved_path,
            "audio_base64": base64.b64encode(audio_bytes_out).decode("utf-8")
        }

    def _extract_json(self, raw_text: str) -> Dict[str, Any]:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        candidate = match.group(1).strip() if match else raw_text.strip()

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1:
            candidate = candidate[start:end+1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return {
                "spoken_reply": raw_text.strip(),
                "detected_language_code": "hi-IN",
                "log_update": {
                    "meals": [],
                    "hydration_liters": 0.0,
                    "workout": {"activity": "", "duration_min": 0, "status": "none"},
                    "sleep": {"hours": 0.0, "quality_1_to_5": 0},
                    "energy_level": "unknown"
                },
                "adaptive_action": "Parsed raw text response"
            }
