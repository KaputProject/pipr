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


def print_blockchain(blockchain):
    print("-" * 20)
    for block in blockchain.chain:
        print(f"Index: {block.index}")
        print(f"  Timestamp: {block.timestamp}")
        print(f"  Data: {block.data}")
        print(f"  Difficulty: {block.difficulty}")
        print(f"  Nonce: {block.nonce}")
        print(f"  Miner: {block.miner}")
        print(f"  Previous Hash: {block.previous_hash}")
        print(f"  Hash: {block.hash}")
        print("-" * 20)
    print(f"Total Blocks: {len(blockchain.chain)}\n")


def print_stats(blockchain):
    print("Blockchain Statistics:")
    print(f"Total Blocks: {len(blockchain.chain)}")
    print(f"Current Difficulty: {blockchain.difficulty}")

    if len(blockchain.chain) < 2:
        print("Not enough blocks to calculate mining stats.")
        return

    total_time = blockchain.chain[-1].timestamp - blockchain.chain[0].timestamp
    num_blocks = len(blockchain.chain) - 1

    blocks_per_sec = num_blocks / total_time if total_time > 0 else 0
    sec_per_block = total_time / num_blocks if num_blocks > 0 else 0

    print(f"Total Mining Time: {total_time:.4f} s")
    print(f"Blocks per Second: {blocks_per_sec:.4f}")
    print(f"Seconds per Block: {sec_per_block:.4f}")
