import json
import audioop
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np
import torch
from omnivoice import OmniVoice
from pathlib import Path
import soundfile as sf
import sys
import time

# Load the model once, then reuse it for every request.
torch.set_num_threads(4)

print("Loading OmniVoice...", flush=True)

model = OmniVoice.from_pretrained(
    "k2-fsa/OmniVoice",
    device_map="cuda:0",
    dtype=torch.float16,
    load_asr=False,
)

reference_path = Path("/work/female_reference.wav")

reference_text = (
    "Hello, I am G1. "
    "I am happy to talk with you in English and Japanese."
)

# Create the reference only once.
# Later restarts reuse the saved voice.
if not reference_path.exists():
    print("Creating a female reference voice...", flush=True)

    reference_audio = model.generate(
        text=reference_text,
        language="en",
        instruct="female, young adult, moderate pitch",
        num_step=32,
    )

    sf.write(
        str(reference_path),
        reference_audio[0],
        model.sampling_rate,
    )

# Encode the reference once when the server starts.
voice_prompt = model.create_voice_clone_prompt(
    ref_audio=str(reference_path),
    ref_text=reference_text,
)

class VoiceHandler(BaseHTTPRequestHandler):
    def send_data(self, status, data, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/synthesize":
            self.send_data(404, b"Unknown endpoint", "text/plain")
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))

            if not 0 < size <= 65536:
                raise ValueError("Invalid request size")

            payload = json.loads(self.rfile.read(size))
            text = payload["text"]
            language = payload.get("language", "en")

            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a nonempty string")

            if language not in ("en", "ja"):
                raise ValueError("Language must be en or ja")

        except (ValueError, KeyError, TypeError, AttributeError) as error:
            self.send_data(400, str(error).encode(), "text/plain")
            return

        try:
            print("Generating:", text, flush=True)

            torch.cuda.synchronize()
            started = time.monotonic()

            result = model.generate(
                text=text,
                language=language,
                voice_clone_prompt=voice_prompt,
                num_step=8,
            )

            torch.cuda.synchronize()
            elapsed = time.monotonic() - started
            duration = len(result[0]) / model.sampling_rate

            audio = np.asarray(result[0])

            print(
                f"Generation: {elapsed:.2f}s | "
                f"Audio duration: {duration:.2f}s",
                flush=True,
            )

            if audio.ndim != 1 or not audio.size:
                raise RuntimeError("Expected nonempty mono audio")

            if not np.isfinite(audio).all():
                raise RuntimeError("Audio contains invalid samples")

            # Convert floating-point audio to signed 16-bit PCM.
            pcm = (
                np.clip(audio, -1.0, 1.0) * 32767
            ).astype("<i2").tobytes()

            # G1's existing speaker code expects 16 kHz.
            if model.sampling_rate != 16000:
                pcm, _ = audioop.ratecv(
                    pcm, 2, 1,
                    model.sampling_rate, 16000, None,
                )

        except Exception as error:
            print("Generation failed:", error, flush=True)
            self.send_data(500, str(error).encode(), "text/plain")
            return

        self.send_data(200, pcm, "application/octet-stream")


server = HTTPServer(("0.0.0.0", 8001), VoiceHandler)

print("OmniVoice server ready on port 8001", flush=True)

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("Stopping server.", flush=True)
finally:
    server.server_close()
