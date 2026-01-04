import hashlib
import socket
import threading
import json
import time
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from block import Block
from blockchain import Blockchain
import interface

HOST = '127.0.0.1'
PORT = 8008
peers = []

difficulty = 4
blockchain = Blockchain(difficulty)
blockchain_lock = threading.Lock()

mining_reset = threading.Event()

interval_generiranja_blokov = 2
interval_popravka_tezavnosti = 10
run = True

def start_server():
    global PORT, HOST

    while True:
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((HOST, PORT))
            server_socket.listen(5)
            print(f"Server listening on {HOST}:{PORT}")
            return server_socket
        except Exception:
            print(f"Port {PORT} is busy, trying port {PORT + 1}.")
            PORT += 1
            continue
    return None

def adjust_difficulty():
    global difficulty, diff_label

    if blockchain.chain[-1].index % interval_popravka_tezavnosti == 0:
        previous = blockchain.chain[-interval_popravka_tezavnosti]
        time_expected = interval_popravka_tezavnosti * interval_generiranja_blokov
        time_taken = blockchain.chain[-1].timestamp - previous.timestamp

        if time_taken < time_expected / 2:
            difficulty = blockchain.chain[-1].difficulty + 1
            blockchain.difficulty = difficulty
            # interface.update_display(display, f"Difficulty increased to {difficulty}", "green")
        elif time_taken > time_expected * 2:
            difficulty = blockchain.chain[-1].difficulty - 1
            blockchain.difficulty = difficulty
            # interface.update_display(display, f"Difficulty decreased to {difficulty}", "green")

        diff_label.config(text=f"Difficulty: {difficulty}")

def comulative_difficulty(blocks):
    return sum([2**block.difficulty for block in blocks])

def handle_received_blockchain(received_blocks):
    global difficulty, run

    with blockchain_lock:
        if received_blocks == blockchain.chain:
            return

        if not is_chain_valid(received_blocks):
            interface.update_display(display, "Received blocks declined. Blockchain NOT valid.", "red")
            return

        d1 = comulative_difficulty(received_blocks)
        d2 = comulative_difficulty(blockchain.chain)

        if d1 > d2:
            blockchain.chain = received_blocks
            adjust_difficulty()

            interface.update_blockchain_display(blockchain_display, blockchain)
            interface.update_display(display, f"Received blocks accepted. Blockchain with the CD of {d1} replaces {d2}","green")

            run = False
            broadcast_blockchain()
        else:
            interface.update_display(display, "Received blocks rejected. Blockchain not updated.", "red")

def handle_receive(sender_socket, addr):
    try:
        with sender_socket:
            message = sender_socket.recv(1000000).decode()
            blocks_data = json.loads(message)

            received_blocks = []
            for block_data in blocks_data:
                block = Block(
                    index=block_data['index'],
                    timestamp=block_data['timestamp'],
                    data=block_data['data'],
                    difficulty=block_data['difficulty'],
                    miner=block_data['miner'],
                    previous_hash=block_data['previous_hash'],
                    nonce=block_data['nonce']
                )
                received_blocks.append(block)

            interface.update_display(display, f"Received {len(received_blocks)} blocks from {addr}. Validating...")

            handle_received_blockchain(received_blocks)
    except Exception as e:
        interface.update_display(display, f"Error handling received blocks: {e}")

def accept_connections(sock):
    try:
        while True:
            sender_socket, addr = sock.accept()
            threading.Thread(target=handle_receive, args=(sender_socket, addr), daemon=True).start()
    except Exception as e:
        interface.update_display(display, f"Error accepting connections: {e}")
    finally:
        sock.close()

def add_peer(peer_entry):
    peer = peer_entry.get().strip()
    if peer and peer not in peers:
        peers.append(peer)
        interface.update_display(display, f"Peer added: {peer}")

def start_mining(blockchain):
    threading.Thread(target=mine, args=(blockchain,), daemon=True).start()

def mine(blockchain):
    global run

    while True:
        run = True

        try:
            new_block = Block(
                index=len(blockchain.chain),
                timestamp=time.time(),
                data=f"Block {len(blockchain.chain)}",
                difficulty=blockchain.difficulty,
                miner=PORT,
                previous_hash=blockchain.get_latest_block().hash
            )

            interface.update_display(display, "Mining new block...")

            target = "0" * blockchain.difficulty

            while new_block.hash[:new_block.difficulty] != target and run:
                new_block.nonce += 1
                new_block.hash = new_block.calculate_hash()

            if not run:
                interface.update_display(display, "Mining reset. Mining new block...", "red")
                continue

            blockchain.add_block(new_block)

            interface.update_blockchain_display(blockchain_display, blockchain)
            interface.update_display(display, "New block mined and broadcast.", "green")

            with blockchain_lock:
                broadcast_blockchain()
        except Exception as e:
            print(e)
            interface.update_display(display, f"Error mining: {e}", "red")


def is_chain_valid(chain):
    for i in range(1, len(chain)):
        current_block = chain[i]
        previous_block = chain[i - 1]

        if current_block.previous_hash != previous_block.hash:
            return False

        if current_block.hash != current_block.calculate_hash():
            return False

    return True

def broadcast_blockchain():
    serialized_chain = json.dumps([block.__dict__ for block in blockchain.chain])
    adjust_difficulty()
    for peer in peers:
        try:
            ip, port = peer.split(':')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, int(port)))
                s.sendall(serialized_chain.encode())
        except Exception as e:
            peers.remove(peer)

def main():
    global display, blockchain_display, blockchain, diff_label

    sock = start_server()
    if sock is None:
        print("Error finding an open port!")
        return

    threading.Thread(target=accept_connections, args=(sock,), daemon=True).start()

    root = tk.Tk()
    root.title("Blockchain P2P Network")

    status_frame = tk.Frame(root)
    status_frame.pack(anchor="w", padx=5, pady=5)

    status_label = tk.Label(status_frame, text=f"Online: PORT {PORT}", font=("Arial", 10, "bold"))
    status_label.pack(side="left", padx=5)

    diff_label = tk.Label(status_frame, text=f"Difficulty: {difficulty}", font=("Arial", 10, "bold"))
    diff_label.pack(side="left", padx=5)

    peer_frame = tk.Frame(root)
    peer_frame.pack(anchor="w", padx=5, pady=5)

    peer_label = tk.Label(peer_frame, text="Add Peer (IP:Port):")
    peer_label.pack(side="left", padx=5)

    peer_entry = tk.Entry(peer_frame, width=40)
    peer_entry.insert(0, "127.0.0.1:800")
    peer_entry.pack(side="left", padx=5)

    connect_button = tk.Button(peer_frame, text="Connect Peer", command=lambda: add_peer(peer_entry))
    connect_button.pack(side="left", padx=5)

    mine_button = tk.Button(peer_frame, text="Mine", command=lambda: start_mining(blockchain))
    mine_button.pack(side="left", padx=5)

    displays_frame = tk.Frame(root)
    displays_frame.pack(anchor="w", padx=5, pady=5)

    blockchain_frame = tk.Frame(displays_frame)
    blockchain_frame.pack(side="left", padx=5)

    blockchain_label = tk.Label(blockchain_frame, text="Blockchain:")
    blockchain_label.pack(anchor="w", padx=5)

    blockchain_display = ScrolledText(blockchain_frame, wrap=tk.WORD, state='disabled', height=15, width=40)
    blockchain_display.pack(anchor="w", padx=5)

    peer_display_frame = tk.Frame(displays_frame)
    peer_display_frame.pack(side="left", padx=5)

    peer_label = tk.Label(peer_display_frame, text="Peer Connections:")
    peer_label.pack(anchor="w", padx=5)

    display = ScrolledText(peer_display_frame, wrap=tk.WORD, state='disabled', height=15, width=40)
    display.pack(anchor="w", padx=5)

    display.tag_configure("green", foreground="green")
    display.tag_configure("red", foreground="red")

    root.mainloop()

    interface.update_blockchain_display(blockchain_display, blockchain)

if __name__ == "__main__":
    main()
