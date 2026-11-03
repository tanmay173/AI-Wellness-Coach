import os
import base64
from dotenv import load_dotenv

# Load .env before initializing SarvamAI
load_dotenv()

from sarvamai import SarvamAI

def main():
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise ValueError("SARVAM_API_KEY environment variable not set")
    
    print("[1/2] Connecting to Sarvam AI with configured API key...")
    client = SarvamAI(api_subscription_key=api_key)

    print("[2/2] Requesting Text-to-Speech synthesis (bulbul:v3)...")
    test_text = "Namaste! Main aapka AI Wellness Coach hoon. Sab ready hai!"
    response = client.text_to_speech.convert(
        text=test_text,
        language_code="hi-IN",
        speaker="aditya",
        model="bulbul:v3",
        output_audio_codec="wav"
    )

    if response.audios and len(response.audios) > 0:
        audio_bytes = base64.b64decode(response.audios[0])
        output_file = "output.wav"
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        print(f"Success! Audio successfully generated and saved to '{output_file}' ({len(audio_bytes)} bytes).")
    else:
        print("Received response, but no audio data was returned.")

if __name__ == "__main__":
    main()
