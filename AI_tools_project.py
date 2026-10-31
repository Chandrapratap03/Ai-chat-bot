
import tkinter as tk
from tkinter import messagebox
import urllib.request
import urllib.error
import json
import threading
import time
import os

# ---------------- CONFIGURATION ----------------

MODEL = "gemini-3.5-flash-lite"
KEY_FILE = "AQ.Ab8RN6JsooCaymg1s1dfnNpXsvtDBQ-JDrBfjHzpyr6tqTtyBg"

BG = "#111827"
PANEL = "#1F2937"
INPUT_BG = "#273449"
ACCENT = "#7C5CFC"
TEXT = "#F9FAFB"
MUTED = "#9CA3AF"
GREEN = "#86EFAC"
BLUE = "#A5B4FC"

chat_history = []
busy = False
show_key = False

# ---------------- API KEY FUNCTIONS ----------------

def load_api_key():
    try:
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "r", encoding="utf-8") as file:
                return file.read().strip()
    except OSError:
        pass

    return ""


def save_api_key():
    key = api_entry.get().strip()

    if not key:
        messagebox.showwarning(
            "Missing API Key",
            "Please enter your Gemini API key."
        )
        return

    try:
        with open(KEY_FILE, "w", encoding="utf-8") as file:
            file.write(key)

        status_label.config(text="API key saved on this computer.")
        messagebox.showinfo(
            "Success",
            "Your API key has been saved."
        )

    except OSError as error:
        messagebox.showerror(
            "Save Error",
            str(error)
        )


def toggle_key_visibility():
    global show_key
    show_key = not show_key

    if show_key:
        api_entry.config(show="")
        show_key_button.config(text="Hide")
    else:
        api_entry.config(show="*")
        show_key_button.config(text="Show")


# ---------------- CHAT DISPLAY ----------------

def add_message(sender, message, tag):
    chat_box.config(state="normal")
    chat_box.insert(tk.END, sender + "\n", tag)
    chat_box.insert(tk.END, message + "\n\n", "message")
    chat_box.config(state="disabled")
    chat_box.see(tk.END)


def show_welcome():
    add_message(
        "Gemini AI",
        "Welcome! Enter and save your API key above, "
        "then tell me what you want me to do.\n\n"
        "Examples:\n"
        "• Make notes on artificial intelligence\n"
        "• Explain Python loops with examples\n"
        "• Summarize a paragraph\n"
        "• Write a Python program",
        "assistant"
    )


# ---------------- SEND MESSAGE ----------------

def send_message(event=None):
    global busy

    question = prompt_entry.get().strip()

    if not question:
        return "break"

    if busy:
        return "break"

    api_key = api_entry.get().strip()

    if not api_key:
        messagebox.showwarning(
            "API Key Required",
            "Enter your Gemini API key in the top box first."
        )
        return "break"

    add_message("You", question, "user")
    prompt_entry.delete(0, tk.END)

    busy = True
    send_button.config(state="disabled")
    status_label.config(text="Gemini is working on your task...")

    chat_box.config(state="normal")
    chat_box.insert(tk.END, "Gemini AI\n", "assistant")
    chat_box.insert(tk.END, "Thinking...\n\n", "system")
    chat_box.config(state="disabled")
    chat_box.see(tk.END)

    threading.Thread(
        target=call_gemini,
        args=(api_key, question),
        daemon=True
    ).start()

    return "break"


# ---------------- GEMINI API ----------------

def call_gemini(api_key, question):
    global chat_history

    answer = ""

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/" + MODEL + ":generateContent"
    )

    # Send previous conversation so follow-up questions work.
    messages = chat_history + [
        {"role": "user", "parts": [{"text": question}]}
    ]

    data = {
        "contents": messages,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096
        }
    }

    for attempt in range(3):
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                },
                method="POST"
            )

            with urllib.request.urlopen(
                request, timeout=120
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            candidates = result.get("candidates", [])

            if not candidates:
                answer = (
                    "Gemini returned no response. "
                    "Please try a different prompt."
                )
                break

            candidate = candidates[0]

            parts = candidate.get(
                "content", {}
            ).get("parts", [])

            answer = "\n".join(
                part["text"]
                for part in parts
                if "text" in part
            )

            if not answer:
                answer = "Gemini returned no text. Please try again."
                break

            # Update conversation only after a successful response.
            chat_history.append({
                "role": "user",
                "parts": [{"text": question}]
            })

            chat_history.append({
                "role": "model",
                "parts": [{"text": answer}]
            })

            break

        except urllib.error.HTTPError as error:
            details = error.read().decode(
                "utf-8", errors="replace"
            )

            try:
                error_data = json.loads(details)
                details = error_data.get(
                    "error", {}
                ).get("message", details)
            except json.JSONDecodeError:
                pass

            if error.code in (500, 502, 503, 504):
                if attempt < 2:
                    root.after(
                        0,
                        lambda: status_label.config(
                            text="Server busy. Retrying..."
                        )
                    )
                    time.sleep(2 ** (attempt + 1))
                    continue

            if error.code == 429:
                answer = (
                    "API quota or rate limit reached.\n"
                    "Check your Google AI Studio usage and limits.\n\n"
                    + details
                )
            else:
                answer = (
                    "API Error " + str(error.code)
                    + ":\n" + details
                )

            break

        except Exception as error:
            if attempt < 2:
                root.after(
                    0,
                    lambda: status_label.config(
                        text="Connection issue. Retrying..."
                    )
                )
                time.sleep(2 ** (attempt + 1))
                continue

            answer = (
                "Connection error: " + str(error)
                + "\nCheck your internet connection."
            )
            break

    root.after(0, finish_response, answer)


# ---------------- DISPLAY RESPONSE ----------------

def finish_response(answer):
    global busy

    # Remove the temporary Thinking message.
    chat_box.config(state="normal")
    content = chat_box.get("1.0", tk.END)
    position = content.rfind("Thinking...\n")

    if position != -1:
        start = "1.0 + " + str(position) + " chars"
        end = start + " + " + str(len("Thinking...\n")) + " chars"
        chat_box.delete(start, end)

    chat_box.config(state="disabled")

    add_message("Gemini AI", answer, "assistant")

    busy = False
    send_button.config(state="normal")
    status_label.config(text="Ready")
    prompt_entry.focus_set()


# ---------------- CLEAR CHAT ----------------

def clear_chat():
    global chat_history

    chat_history = []
    chat_box.config(state="normal")
    chat_box.delete("1.0", tk.END)
    chat_box.config(state="disabled")

    show_welcome()
    status_label.config(text="Conversation cleared.")


# ---------------- MAIN WINDOW ----------------

root = tk.Tk()
root.title("Gemini AI Assistant")
root.geometry("900x720")
root.minsize(650, 500)
root.configure(bg=BG)

root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(2, weight=1)

# ---------------- HEADER ----------------

header = tk.Frame(root, bg=PANEL, padx=20, pady=14)
header.grid(row=0, column=0, sticky="ew")

tk.Label(
    header,
    text="✦",
    font=("Arial", 28, "bold"),
    fg=ACCENT,
    bg=PANEL
).pack(side="left", padx=(0, 12))

title_frame = tk.Frame(header, bg=PANEL)
title_frame.pack(side="left")

tk.Label(
    title_frame,
    text="Gemini AI Assistant",
    font=("Arial", 20, "bold"),
    fg=TEXT,
    bg=PANEL
).pack(anchor="w")

tk.Label(
    title_frame,
    text="Ask questions, create notes, and complete tasks",
    font=("Arial", 10),
    fg=MUTED,
    bg=PANEL
).pack(anchor="w", pady=(3, 0))

# ---------------- API KEY PANEL ----------------

key_panel = tk.Frame(root, bg=PANEL, padx=15, pady=10)
key_panel.grid(row=1, column=0, sticky="ew", padx=12, pady=(10, 0))
key_panel.grid_columnconfigure(1, weight=1)

tk.Label(
    key_panel,
    text="Gemini API Key",
    bg=PANEL,
    fg=TEXT,
    font=("Arial", 10, "bold")
).grid(row=0, column=0, padx=(0, 10))

api_entry = tk.Entry(
    key_panel,
    show="*",
    bg=INPUT_BG,
    fg=TEXT,
    insertbackground=TEXT,
    font=("Arial", 11),
    bd=0
)
api_entry.grid(row=0, column=1, sticky="ew", ipady=7, padx=5)

show_key_button = tk.Button(
    key_panel,
    text="Show",
    command=toggle_key_visibility,
    bg=INPUT_BG,
    fg=TEXT,
    bd=0,
    cursor="hand2",
    padx=8
)
show_key_button.grid(row=0, column=2, padx=4)

save_key_button = tk.Button(
    key_panel,
    text="Save Key",
    command=save_api_key,
    bg=ACCENT,
    fg="white",
    activebackground="#6544E8",
    bd=0,
    cursor="hand2",
    font=("Arial", 9, "bold"),
    padx=12,
    pady=7
)
save_key_button.grid(row=0, column=3, padx=(4, 0))

# Load the saved key automatically.
saved_key = load_api_key()

if saved_key:
    api_entry.insert(0, saved_key)

# ---------------- CHAT AREA ----------------

chat_frame = tk.Frame(root, bg=BG, padx=15, pady=12)
chat_frame.grid(row=2, column=0, sticky="nsew")
chat_frame.grid_columnconfigure(0, weight=1)
chat_frame.grid_rowconfigure(0, weight=1)

scrollbar = tk.Scrollbar(chat_frame)
scrollbar.grid(row=0, column=1, sticky="ns")

chat_box = tk.Text(
    chat_frame,
    bg=BG,
    fg=TEXT,
    font=("Segoe UI", 11),
    wrap="word",
    padx=12,
    pady=12,
    bd=0,
    relief="flat",
    yscrollcommand=scrollbar.set,
    state="disabled"
)
chat_box.grid(row=0, column=0, sticky="nsew")
scrollbar.config(command=chat_box.yview)

chat_box.tag_configure(
    "user",
    foreground=BLUE,
    font=("Segoe UI", 11, "bold"),
    spacing1=10
)

chat_box.tag_configure(
    "assistant",
    foreground=GREEN,
    font=("Segoe UI", 11, "bold"),
    spacing1=10
)

chat_box.tag_configure(
    "message",
    foreground=TEXT,
    font=("Segoe UI", 11),
    lmargin1=10,
    lmargin2=10,
    spacing3=8
)

chat_box.tag_configure(
    "system",
    foreground=MUTED,
    font=("Segoe UI", 10, "italic")
)

# ---------------- INPUT PANEL ----------------

bottom = tk.Frame(root, bg=PANEL, padx=15, pady=12)
bottom.grid(row=3, column=0, sticky="ew")
bottom.grid_columnconfigure(0, weight=1)

prompt_entry = tk.Entry(
    bottom,
    bg=INPUT_BG,
    fg=TEXT,
    insertbackground=TEXT,
    font=("Segoe UI", 12),
    bd=0
)
prompt_entry.grid(
    row=0, column=0, sticky="ew",
    padx=(0, 8), ipady=12
)
prompt_entry.bind("<Return>", send_message)

send_button = tk.Button(
    bottom,
    text="Send ➤",
    command=send_message,
    bg=ACCENT,
    fg="white",
    activebackground="#6544E8",
    font=("Segoe UI", 10, "bold"),
    bd=0,
    cursor="hand2",
    padx=18,
    pady=9
)
send_button.grid(row=0, column=1)

status_label = tk.Label(
    bottom,
    text="Ready",
    bg=PANEL,
    fg=MUTED,
    font=("Arial", 9)
)
status_label.grid(row=1, column=0, sticky="w", pady=(10, 0))

clear_button = tk.Button(
    bottom,
    text="Clear Chat",
    command=clear_chat,
    bg=PANEL,
    fg=BLUE,
    activebackground=PANEL,
    activeforeground=TEXT,
    font=("Arial", 9),
    bd=0,
    cursor="hand2"
)
clear_button.grid(row=1, column=1, sticky="e", pady=(8, 0))

# ---------------- START ----------------

show_welcome()
prompt_entry.focus_set()

root.mainloop()
