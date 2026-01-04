import hashlib

class Block:
    def __init__(self, index, data, timestamp, difficulty, miner, previous_hash, nonce = 0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.difficulty = difficulty
        self.nonce = nonce
        self.miner = miner
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        sha = hashlib.sha256()
        sha.update(
            str(self.index).encode('utf-8') +
            str(self.timestamp).encode('utf-8') +
            str(self.data).encode('utf-8') +
            str(self.previous_hash).encode('utf-8') +
            str(self.difficulty).encode('utf-8') +
            str(self.nonce).encode('utf-8')
        )
        return sha.hexdigest()

    def mine_block(self, reset):
        target = "0" * self.difficulty

        while self.hash[:self.difficulty] != target:
            if reset.is_set():
                return False
            self.nonce += 1
            self.hash = self.calculate_hash()

        return True