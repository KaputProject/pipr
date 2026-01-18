import threading
import time
import multiprocessing
from multiprocessing import Event
from block import Block
from blockchain import Blockchain
from server import logger
from utils.blockchainUtils import *
from collections import deque
from utils.mqttListener import MqttListener
import json

fixed_difficulty = 5
num_threads = 1
show_stats = True
block_limit = 50

start_difficulty = 4
interval_generiranja_blokov = 20
interval_popravka_tezavnosti = 10
received_data = deque()
topic = "blockchain/upload"

def init_worker(event):
    global stop_event
    stop_event = event


def mine_worker(args):
    difficulty, data, previous_hash, start_nonce, step, index = args
    nonce = start_nonce
    target = "0" * difficulty

    block = Block(
        index=index,
        timestamp=time.time(),
        data=f"{data}",
        difficulty=difficulty,
        miner="hmmmmmm",
        previous_hash=previous_hash
    )

    counter = 0
    check_interval = 100
    while True:
        if counter % check_interval == 0 and stop_event.is_set():
            return None

        block.nonce = nonce
        hash_value = block.calculate_hash()
        counter += 1

        if hash_value.startswith(target):
            block.hash = hash_value
            block.miner = f"miner_{start_nonce}"
            stop_event.set()
            return block
        nonce += step

def mine(blockchain):
    if num_threads is None:
        num_processes = multiprocessing.cpu_count()
    else:
        num_processes = num_threads

    stop_event = Event()
    pool = multiprocessing.Pool(processes=num_processes, initializer=init_worker, initargs=(stop_event,))

    try:
        while True:
            if block_limit and len(blockchain.chain) >= block_limit:
                print("Dosežen limit blokov, ustavitev rudarjenja.")
                break

            latest_block = blockchain.get_latest_block()
            stop_event.clear()
            if(received_data):
                data = received_data.popleft()

            else:
                data = latest_block.index + 1

            tasks = []
            for i in range(num_processes):
                tasks.append((blockchain.difficulty,data, latest_block.hash, i, num_processes,latest_block.index + 1))

            for result_block in pool.imap_unordered(mine_worker, tasks):
                if result_block:
                    if blockchain.is_new_block_valid(result_block):
                        blockchain.add_block(result_block)
                        print_block(result_block)
                        break

            if fixed_difficulty is None:
                blockchain.adjust_difficulty()

    except Exception as e:
        print(f"Napaka pri rudarjenju: {e}")
    finally:
        pool.close()
        pool.join()

def main():
    mqtt_listener = MqttListener(topic=topic, data_queue=received_data, logger=logger)
    mqtt_listener.start()
    received_data.append("Initial block data")

    if fixed_difficulty is None:
        difficulty = start_difficulty
    else:
        difficulty = fixed_difficulty

    blockchain = Blockchain(difficulty, interval_generiranja_blokov, interval_popravka_tezavnosti)
    mine(blockchain)

    if show_stats:
        print_stats(blockchain)


if __name__ == "__main__":
    RUN_MPI_MINING = True
    if RUN_MPI_MINING:
        import mpi_mining
        mpi_mining.main()
    else:
        main()
