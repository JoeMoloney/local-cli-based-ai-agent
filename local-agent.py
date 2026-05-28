#!/usr/bin/env python3
import os
import sys
import requests
import json
import readline

def gather_context():
    """Scans the active directory and extracts file contents for the AI context."""
    current_dir = os.getcwd()
    files_context = []
    
    for file in os.listdir(current_dir):
        # Ignore hidden files, directories, build artifacts, and the script itself
        if os.path.isfile(file) and not file.startswith('.') and file != 'local-codex':
            try:
                with open(file, 'r', errors='ignore') as f:
                    files_context.append(f"--- FILE: {file} ---\n{f.read(4000)}\n") # Bumped to 4k chars
            except Exception:
                pass
                
    context_payload = "\n".join(files_context)
    return f"You are a local CLI terminal coding assistant working inside: {current_dir}.\nHere is the active file content:\n{context_payload}"

def main():
    print("=" * 60)
    print(f"Local Codex Interactive Shell Connected to Ollama")
    print(f"Active Directory: {os.getcwd()}")
    print("Type 'exit' or 'quit' to close the shell, or 'refresh' to re-scan files.")
    print("=" * 60)

    # Gather context once at startup
    system_instruction = gather_context()

    while True:
        try:
            # Create a custom prompt indicator
            user_input = input("\ncodex> ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            if user_input.lower() == 'refresh':
                print("Re-scanning directory for file changes...")
                system_instruction = gather_context()
                print("Context updated.")
                continue

            print("AI-ing... 👀👀👀")
            
            # 1. Set stream to True AND add stream=True to the requests call
            response = requests.post("http://localhost:11434/api/generate", json={
                "model": "gemma3:27b",
                "system": system_instruction,
                "prompt": user_input,
                "stream": True # <-- Keeps Ollama streaming
            }, stream=True)    # <-- Tells Python to keep the connection open
            
            if response.status_code == 200:
                print("\ncodex> ", end="", flush=True)
                
                # 2. Loop through the incoming data line-by-line as it arrives
                for line in response.iter_lines():
                    if line:
                        try:
                            # Parse each tiny word-chunk JSON object
                            chunk = json.loads(line.decode('utf-8'))
                            word = chunk.get("response", "")
                            # Print the word instantly without a newline
                            print(word, end="", flush=True)
                        except Exception:
                            pass
                print() # Print a final blank line when the stream finishes
            else:
                print(f"\nError: Ollama returned status code {response.status_code}")

                
        except KeyboardInterrupt:
            # Gracefully handle Ctrl+C to clear the line instead of crashing
            print("\nUse 'exit' to quit.")
        except requests.exceptions.ConnectionError:
            print("\nConnection Error: Is Ollama running? Try 'systemctl status ollama'")
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
