#!/usr/bin/env python3
import os
import sys
import requests
import json
import readline
import re
import select

def gather_context():
    """Scans the active directory and extracts file contents for the AI context."""
    current_dir = os.getcwd()
    files_context = []
    
    for file in os.listdir(current_dir):
        if os.path.isfile(file) and not file.startswith('.') and file != 'local-codex':
            try:
                with open(file, 'r', errors='ignore') as f:
                    files_context.append(f"--- FILE: {file} ---\n{f.read(4000)}\n")
            except Exception:
                pass
                
    context_payload = "\n".join(files_context)
    return (
        f"You are a local CLI terminal coding assistant working inside: {current_dir}.\n"
        f"Here is the active file content:\n{context_payload}\n\n"
        "CRITICAL FILE WRITING CAPABILITY:\n"
        "If the user asks you to create or modify a file or folder, you can do it by using this EXACT format in your response:\n"
        "===[CREATE_FILE: path/to/filename.ext]===\n"
        "Your code or file content here\n"
        "===[END_FILE]===\n"
        "You can output multiple file blocks in one response. I will intercept them and save them to disk automatically."
    )

def handle_file_creation(ai_text):
    """Parses the AI's response text and writes files/folders to disk."""
    pattern = r"===\[CREATE_FILE:\s*(.*?)\]===\n(.*?)\n===\[END_FILE\]==="
    matches = re.findall(pattern, ai_text, re.DOTALL)
    
    if not matches:
        return
        
    print("\n💾 File System Updates Detected:")
    for filepath, content in matches:
        filepath = filepath.strip()
        dirname = os.path.dirname(filepath)
        
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
            print(f"  📁 Created directory: {dirname}/")
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        print(f"  📄 Written file: {filepath}")

def get_multiline_input():
    """Reads input normally, but collects full streams instantly if a paste event occurs."""
    # Read the very first line entered by the user
    first_line = input("codex> ")
    lines = [first_line]
    
    # Check if there is more text immediately following it in the terminal buffer (pasted data)
    # 0.1 second timeout is the sweet spot for catching programmatic paste streams
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        if ready:
            next_line = sys.stdin.readline().rstrip('\r\n')
            lines.append(next_line)
        else:
            # No more data incoming, paste stream has ended
            break
            
    return "\n".join(lines).strip()

def main():
    print("=" * 60)
    print(f"🤖 Local Codex (Auto Paste-Detect) Connected to Ollama")
    print(f"📂 Active Directory: {os.getcwd()}")
    print("Type normally, or paste blocks freely. Press Enter to send! 👀")
    print("=" * 60)

    system_instruction = gather_context()

    while True:
        try:
            # Call the smart timing input collector
            user_input = get_multiline_input()
            
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            if user_input.lower() == 'refresh':
                print("🔄 Re-scanning directory...")
                system_instruction = gather_context()
                print("✅ Context updated.")
                continue

            print("Thinking... 👀")
            
            response = requests.post("http://localhost:11434/api/generate", json={
                "model": "gemma3:27b",
                "system": system_instruction,
                "prompt": user_input,
                "stream": True,
                "options": {
                    "num_ctx": 32768,
                    "num_predict": 4096
                }
            }, stream=True)

            if response.status_code == 200:
                print("\n--- AI Response ---")
                full_response_buffer = []

                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            word = chunk.get("response", "")
                            print(word, end="", flush=True)
                            full_response_buffer.append(word)
                        except Exception:
                            pass
                print("\n-------------------")

                complete_text = "".join(full_response_buffer)
                handle_file_creation(complete_text)
                
            else:
                print(f"\n❌ Error: Ollama returned status code {response.status_code}")
                
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
        except requests.exceptions.ConnectionError:
            print("\n❌ Connection Error: Is Ollama running?")
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
