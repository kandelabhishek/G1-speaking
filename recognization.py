import sys
from pathlib import Path
import time
PROJECT_DIR = Path(__file__).resolve().parent

sys.path.insert(
    0,
    str(PROJECT_DIR / ".runtime" / "voice-deps"),
)

from gorq import ask
import numpy as np
from microphone import receive_g1
from voice import load_voice_engine, synthesize_pcm
from speaker import G1Speaker
import rclpy

from faster_whisper import WhisperModel



def main():
    
    #Initillizes the transcription model wispher. 
    #device = cpu -> Forces the model to run on CPU instead of GPU
    #compute_type->Quantizes the modle into 8 bit intigers, redusing memory usage
    #local_files_only=True -> Prevents the library from trying to connect to the internet
   
    model = WhisperModel(
        str(PROJECT_DIR / ".runtime" / "whisper-tiny"),
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
        local_files_only=True,
    )

    print("loading voice...", flush=True)
    voice_engine = load_voice_engine()

    rclpy.init()
    speaker= None

    try:
            
        speaker = G1Speaker()
        speaker.wait_until_ready()

        while True:
            print("Start speaking. Recording for....", flush=True)
            recording_start = time.monotonic()
            pcm = receive_g1(6)
            print (f"Recording : {time.monotonic()-recording_start:.2f} seconds", flush=True)
            
            #np.frombuffer -> Reads the raw byte string as 1-dimensional array of 16 bit little endian integers.
            #A 16-bit little-endian integer is a 2-byte numerical value stored in computer memory with its least significant byte (LSB) placed at the lowest memory address.
            #.astupe-> converts those integers into 32-bit floating-point numbers.
            #/32768.0 -> Normalizes the 16-bit audio data to a range roughly between -1.0 and 1.0, wich is lite the wisper code.
            #Microphone records a 16-bit Pulse-Code Modulation(PCM). A 16-bit binary number can represent 2^16=65536 unique values.
            #As sound wave oscillate, these numbers are split between positive and negetive. so the amplitude range of 16-bit audio signal is -32,768 to +32,768.
            #Feeding large raw integers into a neural networks causes mathematical instability.Whisper expects the audio wave to be mapped to floating-point decimals ranging exactly form -1.0 to 1.0

            audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32)/32768.0

            print("Transcribing..", flush=True)
            transcription_start = time.monotonic()
            
            #segments,info -> Passes the normalize audio to the wispher model.
            #language=none -> tell the model to detect anguage automatically.
            #vad_filter = True -> Enables the Voice Activity detection filter to strip out silence befre transcribing, preventing hallucinations.
            #condition_on_previous_text -> prevents the mddel from using earlier segments as contexxt, reducing the chance of repeated text glitches.
            #segments -> this variable holds the actual transcribed words
            #info-> The metadata
            
            segments,info = model.transcribe(
                audio,language = None,
                task="transcribe", 
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
                 initial_prompt=(
                    "こんにちは。今日はTechshareでG1と話しています。"
                    "日本語とEnglishを混ぜて話します。"
                    "Hello, let's talk about robots."
                ),
                )
            
            #Faster_wihpher streams its output, it doesnt give one giant string of text. instead in hands out segment.A few words or senteces at a time.
            #segment.text-> it extracts just the transcribed words from that chunk, ignoring the timestamps and other data.
            #.strip()-> Trims empty spaces
            #.join -> Finally, it takes all those cleaned-up text chunks and glues them together into a single string.
            # for segment in segments:
            #     raw_text = segment.text
            #     clean_text=raw_text.strip()
            #     cleaned_text_pieces.append(clean_text)
        
            text = " ".join(segment.text.strip() for segment in segments).strip()
            language = info.language

            print(
                f"Transcription:"
                f"{time.monotonic()-transcription_start:.2f} seconds",
                flush=True,
            )


            print("Detected Language", info.language, flush=True)
            print("text Recognized", text, flush=True)

            if not text:
                print("No speech recognized. Try again.")
                continue

            print("generating reply...", flush=True)


            reply = ask(text,language)
            print("G1 says:", reply)

            #llm.py part
            if not reply or reply.lower().startswith("[error]"):
                continue

            #generates the reply
            print("G1 is generating a speech", flush=True)

            reply_pcm = synthesize_pcm(voice_engine,reply,language,)
            
            print("Playing through G1...", flush=True)
            speaker.play(reply_pcm)

    except KeyboardInterrupt:
        print("\nStopping conversation....Bye Bye")

    finally:
        try:
            if speaker is not None:
                try:
                    speaker.stop()
                except Exception as error:
                    print("Could not confirm playback stop", error)
        finally:
            if speaker is not None:
                speaker.destroy_node()

            if rclpy.ok():
                rclpy.shutdown()




if __name__ == "__main__":
    main()


