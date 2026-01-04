import threading
import time
from block import Block

def is_chain_valid(chain):
    for i in range(1, len(chain)):
        current_block = chain[i]
        previous_block = chain[i - 1]

        if current_block.previous_hash != previous_block.hash:
            return False

        if current_block.hash != current_block.calculate_hash():
            return False

    return True


class Blockchain:
    def __init__(self, difficulty, interval_generiranja_blokov = 2, interval_popravka_tezavnosti = 10):
        self.difficulty = difficulty
        self.chain = [self.create_genesis_block()]
        self.interval_generiranja_blokov = interval_generiranja_blokov
        self.interval_popravka_tezavnosti = interval_popravka_tezavnosti


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


    # Vrne kumulativno težavnost te verige ali te verige z dodanim blokoms
    def comulative_difficulty(self, block=None):
        if block is not None:
            partial = 2 ** block.difficulty
        else:
            partial = 0

        return sum([2 ** block.difficulty for block in self.chain], partial)


    # Dodaj nov blok v verigo, če je veljaven
    def add_block(self, new_block):
        if self.is_new_block_valid(new_block):
            self.chain.append(new_block)
        else:
            raise Exception("Invalid block")


    # Preveri če je celotna veriga veljavna
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.previous_hash != previous_block.hash:
                return False

            if current_block.hash != current_block.calculate_hash():
                return False

        return True


    # Preveri je novi blok veljaven glede na trenutno verigo
    def is_new_block_valid(self, new_block):
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


    # Prilagodi težavnost rudarjenja glede na čas generiranja blokov
    def adjust_difficulty(self):
        latest_block = self.get_latest_block()

        if latest_block.index == 0 or latest_block.index % self.interval_popravka_tezavnosti != 0:
            return

        prilagoditveni_blok = self.chain[len(self.chain) - self.interval_popravka_tezavnosti]
        pricakovan_cas = self.interval_popravka_tezavnosti * self.interval_generiranja_blokov
        dejanski_cas = latest_block.timestamp - prilagoditveni_blok.timestamp

        if dejanski_cas < pricakovan_cas / 2:
            self.difficulty = latest_block.difficulty + 1
            print("Difficulty increased to", self.difficulty)
        elif dejanski_cas > pricakovan_cas * 2:
            self.difficulty = latest_block.difficulty - 1
            print("Difficulty decreased to", self.difficulty)