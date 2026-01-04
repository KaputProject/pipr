import socket
import threading
import json
import time
from block import Block
from blockchain import Blockchain, is_chain_valid
import interface
from old.main import comulative_difficulty

difficulty = 4
interval_generiranja_blokov = 20
interval_popravka_tezavnosti = 10

blockchain = Blockchain(difficulty, interval_generiranja_blokov, interval_popravka_tezavnosti)

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
                miner="hmmmmmm",
                previous_hash=blockchain.get_latest_block().hash
            )

            target = "0" * blockchain.difficulty

            while new_block.hash[:new_block.difficulty] != target and run:
                new_block.nonce += 1
                new_block.hash = new_block.calculate_hash()

            if not run:
                print("Mining reset. Mining new block...", "red")
                continue

            if blockchain.is_new_block_valid(new_block):
                blockchain.add_block(new_block)
                print_block(new_block)
                blockchain.adjust_difficulty()
            else:
                continue

        except Exception as e:
            print("Error mining" + str(e))


def print_block(block):
    print("-" * 20)
    print(f"Index: {block.index}")
    print(f"  Timestamp: {block.timestamp}")
    print(f"  Data: {block.data}")
    print(f"  Difficulty: {block.difficulty}")
    print(f"  Nonce: {block.nonce}")
    print(f"  Miner: {block.miner}")
    print(f"  Previous Hash: {block.previous_hash}")
    print(f"  Hash: {block.hash}")
    print("-" * 20)

def print_blockchain(blockchain_instance):
    print("-" * 20)
    for block in blockchain_instance.chain:
        print(f"Index: {block.index}")
        print(f"  Timestamp: {block.timestamp}")
        print(f"  Data: {block.data}")
        print(f"  Difficulty: {block.difficulty}")
        print(f"  Nonce: {block.nonce}")
        print(f"  Miner: {block.miner}")
        print(f"  Previous Hash: {block.previous_hash}")
        print(f"  Hash: {block.hash}")
        print("-" * 20)
    print(f"Total Blocks: {len(blockchain_instance.chain)}\n")


def main():
    global blockchain

    mine(blockchain)


if __name__ == "__main__":
    main()
