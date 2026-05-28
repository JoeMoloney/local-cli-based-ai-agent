# Local Agent CLI: Troubleshooting History

Details of the environment, network, and Python script issues encountered whilst building and running the Local Agent Interactive Shell on Linux Mint + the respective solutions.

---

## 1. Local Script Cannot Find Ollama (Connection Refused)
### The Issue
The interactive Python script threw connection errors when reaching out to http://localhost:11434, even though the Ollama Docker container was up and running. Running docker ps displayed the port simply as `11434/tcp` without an external mapping arrow.

### Reason
docker-compose.yml was missing the ports configuration block, allow inside-out connections to SearXNG but not outside-in from the interactive shell to the container instance

### Resolution
Added the missing ports block and then took down & re-spun up the container
```yaml
  ollama:
    image: ollama/ollama:latest
    ports: [ "11434:11434" ]
```
```bash
docker compose down && docker compose up -d
```
This bridged the container to the host machine, opening up `0.0.0.0:11434->11434/tcp`.

---

## 2. Token Streaming Crash (Extra data: line 2 column 1)
### The Issue
When setting the Ollama payload option to `"stream": true`, the Python shell immediately crashed upon receiving a response, throwing this exception:
```text
ValueError: Extra data: line 2 column 1 (char 100)
```

### Reason
The script was originally using `response.json()`, which expects one single, complete JSON object. Turning on streaming forces Ollama to change its protocol—it emits data line-by-line as a series of miniature, individual JSON objects separated by newlines. The moment the second token arrived on line 2, Python's single-object parser panicked.

### Resolution
Refactored (Got Google AI to refactor) the network request to keep the connection open (`stream=True` in the request), and wrote a line-by-line streaming iterator loop using a newly imported `json` module:
```python
import json
# ...
response = requests.post(url, json=payload, stream=True) # Open network stream

for line in response.iter_lines():
    if line:
        chunk = json.loads(line.decode('utf-8'))
        print(chunk.get("response", ""), end="", flush=True) # Print tokens live
```

---

## 3. Arrow Keys and History Broken (^[[D^[[D Characters)
### The Issue
Pressing the left/right arrow keys to fix a typo, or pressing the up/down arrow keys to access command history, did not move the cursor. Instead, it printed raw escape strings directly into the prompt line:
```text
codex> test text^[[D^[[D^[[D
```

### Reason
Standard Python terminal `input()` prompts operate in a raw mode that does not naturally interpret terminal control sequences. When you press an arrow key, the terminal transmits a raw hardware escape code sequence (like `^[[D`) which Python treats as literal typed text.

### Resolution
Imported the native Linux **`readline`** module at the top of the script. 
```python
import json
import requests
import readline  # <-- Added this line
```
Simply importing `readline` hooks Python's evaluation wrapper directly into Linux Mint's system-level terminal keyboard drivers. This instantly restored cursor movement, word deletion shortcuts, and command input history scrolling.

---

## 4. Installed Model Mismatch (Blank or Missing Responses)
### The Issue
The script successfully contacted the Docker container but couldn't get a proper response back because it was targeting a model that didn't exist in the local storage volume.

### Reason
The initial placeholder script requested `"model": "qwen2.5-coder:7b"`. Using the active endpoint configuration via `curl http://localhost:11434/api/tags` showed that the active model inside the container environment was gemma3:27b.

### Resolution
Updated the script payload metadata to target the correct available hardware-quantized model identifier string:
```python
"model": "gemma3:27b"
```
