import threading
import tkinter as tk

display_lock = threading.Lock()

def update_display(display, message, color="black"):
    with display_lock:
        display.config(state='normal')
        display.insert(tk.END, message + '\n', color)
        display.config(state='disabled')
        display.see(tk.END)

def update_blockchain_display(display, blockchain):
    with display_lock:
        display.config(state='normal')
        display.delete("1.0", tk.END)
        for block in blockchain.chain:
            display.insert(tk.END, f"Index: {block.index}\n")
            display.insert(tk.END, f"Data: {block.data}\n")
            display.insert(tk.END, f"Timestamp: {block.timestamp}\n")
            display.insert(tk.END, f"Difficulty: {block.difficulty}\n")
            display.insert(tk.END, f"Nonce: {block.nonce}\n")
            display.insert(tk.END, f"Miner: {block.miner}\n")
            display.insert(tk.END, f"Previous hash: {block.previous_hash}\n")
            display.insert(tk.END, f"Hash: {block.hash}\n")
            display.insert(tk.END, "-" * 40 + "\n")
        display.config(state='disabled')
        display.see(tk.END)