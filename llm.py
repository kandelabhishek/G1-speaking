#request allows python to send HTTP requesst to web servers orlocal API
import requests
#port 11434 is OLLAMA default port
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3.5:2b"

def ask(text,language):
    #initilizes a list of dictionaries to format the conversation history for the chat API

    messages = [
        {
            "role":"system",
            "content":(
              "You are G1, a Unitree humanoid robot demonstrating at Techshare. "
    f"Reply in the user's language: {language}. "
    "Be polite, respectful, and natural. "
    "Answer only the question asked, usually in one short sentence. "
    "Use at most two short sentences when an explanation is necessary. "
    "Do not add introductions, unrelated hardware details, or follow-up questions. "
    "If the transcription is unclear, politely ask the user to repeat it. "
    "Never invent observations about wires, objects, or your surroundings. "
    "This program supports voice conversation but cannot execute robot movements. "
    "Do not claim to have performed physical actions. "
    "Use a brief robot pun only when appropriate, and rarely. "
    "Use plain spoken text without emojis, Markdown, or decorative symbols."
            )
        },
        {
            "role":"user",
            "content" : text
        }

    ]

    #Acts as the exact package of instructions and data that python sends to the Ollama server.
    #messages -> passes the messages telling AI rules
    #stream - False -> Tells the server to wait until AI has generated the entire response
    #think : False -> setting it to false ensures the user cannot se the chain-of-thought process.
    #options -> num_cts -> sets the merory size to 2048 tokens. num_predict -> limit to the length of AI's reply.
    payload = {
        "model" : MODEL_NAME,
        "messages" : messages,
        "stream" : False,
        "think" : False,
        "options" : {"num_ctx" : 2048 , "num_predict" : 30, "temperature" : 0.3}
    }

    try:
        #sends an HTTP POST request to OLLAMA URL asn JSON data. It will wait for 60 seconds for a response.
        #response.raise_for_status() -> Checks teh HTTP response code. If the server returned an error, this line forces the python to raise an exception immediately.
        response = requests.post(OLLAMA_URL, json = payload, timeout = 60)
        response.raise_for_status()
        #Prases the successful JSON response from the Ollama server
        data = response.json()
        #safely navigates the response dictionary to extract the generated text. It looks for messages then content and reove any leading trailing whitespace.
        #data.get(key, default_values)-> searches the dictionary for the key "message" If the message exits it returns the value.
        #.get("content", "") -> .get() operates on whatever was returned by the first step.
        #if "content" exists, it retrives the actual text string the AI generated.
        #strip() -> Language models often generates responses with necessary empty spaces or infisible newline characters at the very begining or end of their text.
        return data.get("message", {}).get("content", "").strip()

    except requests.exceptions.RequestException as e:
        return f"[error]:{e}"

# if __name__ == "__main__":
#     reply = ask("Hello. Please introduce yourself briefly.", "en")
#     print(reply)