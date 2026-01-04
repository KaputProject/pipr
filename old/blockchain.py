import threading
import time
from block import Block

class Blockchain:
    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.chain = [self.create_genesis_block()]

    # Ustvari začetni blok
    def create_genesis_block(self):
        genesis_block = Block(
            index=0,
            data="Genesis Block",
            timestamp=time.time(),
            difficulty=self.difficulty,
            miner="System",
            previous_hash="0"
        )
        genesis_block.mine_block(threading.Event())
        return genesis_block

    def get_latest_block(self):
        return self.chain[-1]

    # Dodaj nov blok v verigo, če je veljaven
    def add_block(self, new_block):
        if self.is_chain_valid(new_block):
            self.chain.append(new_block)
        else:
            raise Exception("Invalid block")

    # Preveri je novi blok veljaven glede na trenutno verigo
    def is_chain_valid(self, new_block):
        if new_block.difficulty != self.difficulty:
            return False

        latest_block = self.get_latest_block()

        if new_block.index != latest_block.index + 1:
            return False

        if new_block.previous_hash != latest_block.hash:
            return False

        if new_block.hash != new_block.calculate_hash():
            return False

        if new_block.timestamp < latest_block.timestamp - 60:
            return False

        if new_block.timestamp > time.time() + 60:
            return False

        return True
