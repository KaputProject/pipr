import time
import multiprocessing
from multiprocessing import Event
from block import Block
from blockchain import Blockchain
from utils.blockchainUtils import *

fixed_difficulty = 5
num_threads = None
show_stats = True
block_limit = 100

start_difficulty = 4
interval_generiranja_blokov = 20
interval_popravka_tezavnosti = 10

def init_worker(event):
    global stop_event
    stop_event = event


def mine_worker(args):
    difficulty, index, previous_hash, start_nonce, step = args
    nonce = start_nonce
    target = "0" * difficulty

    block = Block(
        index=index,
        timestamp=time.time(),
        data=f"Block {index}",
        difficulty=difficulty,
        miner="hmmmmmm",
        previous_hash=previous_hash
    )

    # TODO: Mogoce spremeni interval tak da je dinamicen
    counter = 0
    check_interval = 50
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

            tasks = []
            for i in range(num_processes):
                tasks.append((blockchain.difficulty, latest_block.index + 1, latest_block.hash, i, num_processes))

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
    if fixed_difficulty is None:
        difficulty = start_difficulty
    else:
        difficulty = fixed_difficulty

    blockchain = Blockchain(difficulty, interval_generiranja_blokov, interval_popravka_tezavnosti)
    mine(blockchain)

    if show_stats:
        print_stats(blockchain)


if __name__ == "__main__":
    main()
