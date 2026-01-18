"""
MPI simulacija porazdeljenega rudarjenja bločne verige.

Uporablja obstoječe razrede Block in Blockchain.

Struktura:
- Rank 0 (SERVER): Koordinira rudarjenje, zbira rezultate, vzdržuje blockchain, posluša MQTT
- Rank 1+ (WORKERS): Rudarijo bloke z večnitnim rudarjenjem in pošiljajo rezultate strežniku

Uporaba:
    # Direkten zagon:
    python mpi_mining.py
    
    # Z mpiexec (za zagon na več računalnikih):
    mpiexec -n <število_procesov> python mpi_mining.py

Primer:
    python mpi_mining.py
    mpiexec -n 4 python mpi_mining.py
"""

import time
import sys
import os
import subprocess
import multiprocessing
from multiprocessing import Event
from dataclasses import dataclass
from collections import deque
import logging
from typing import Optional, List, Any

# Poskus uvoza mpi4py
try:
    from mpi4py import MPI
except ImportError:
    MPI = None

from utils.mqttListener import MqttListener
from block import Block
from blockchain import Blockchain
from utils.blockchainUtils import print_block, print_stats as stats

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Težavnost rudarjenja (število vodilnih ničel v hashu)
# None = dinamično prilagajanje (začne s start_difficulty)
fixed_difficulty = 4
# Začetna težavnost (če je fixed_difficulty = None)
start_difficulty = 4
# Intervali za dinamično prilagajanje težavnosti
interval_generiranja_blokov = 20
interval_popravka_tezavnosti = 10
# Število blokov za rudarjenje
block_limit = 100
# Število MPI procesov (1 server + N-1 workerjev)
# None = število CPU jeder
num_mpi_processes = 4
# Število niti na workerja za večnitno rudarjenje
# None = število CPU jeder
num_threads = 5
# MQTT nastavitve
use_mqtt = True
mqtt_topic = "blockchain/upload"
# Prikaži statistiko na koncu
show_stats = True

# MPI konstante
SERVER_RANK = 0
TASK_TAG = 0
STOP_TAG = 1
RESULT_TAG = 2
NEW_BLOCK_TAG = 3

received_data = deque()

@dataclass
class TaskMessage:
    """Sporočilo za nalogo rudarjenja."""
    index: int
    data: str
    previous_hash: str
    difficulty: int
    num_threads: int

stop_event = None

def init_worker(event):
    """Inicializira worker proces s stop eventom."""
    global stop_event
    stop_event = event


def mine_worker(args):
    """
    Worker funkcija za rudarjenje bloka.
    OPOMBA: Mora biti top-level funkcija zaradi multiprocessing pickling-a na Windows.
    """
    difficulty, data, previous_hash, start_nonce, step, index, miner_name = args
    nonce = start_nonce
    target = "0" * difficulty

    block = Block(
        index=index,
        timestamp=time.time(),
        data=f"{data}",
        difficulty=difficulty,
        miner=miner_name,
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
            block.miner = f"{miner_name}_{start_nonce}"
            stop_event.set()
            return block
        nonce += step


def mine_block_multithread(task: TaskMessage, rank: int, external_stop_callback=None):

    num_procs = task.num_threads if task.num_threads else multiprocessing.cpu_count()
    
    local_stop_event = Event()
    pool = multiprocessing.Pool(
        processes=num_procs,
        initializer=init_worker,
        initargs=(local_stop_event,)
    )
    
    try:
        # Pripravi naloge za vsak proces
        tasks = []
        for i in range(num_procs):
            tasks.append((
                task.difficulty,
                task.data,
                task.previous_hash,
                i,
                num_procs,
                task.index,
                f"worker_{rank}"
            ))
        
        # Uporabi async da lahko preverjamo za MPI signale
        async_results = [pool.apply_async(mine_worker, (t,)) for t in tasks]
        
        result_block = None
        while True:
            # Preveri za zunanji stop signal (MPI)
            if external_stop_callback and external_stop_callback():
                local_stop_event.set()
                break
            
            # Preveri če je kateri proces našel blok
            for ar in async_results:
                if ar.ready():
                    try:
                        block = ar.get(timeout=0)
                        if block is not None:
                            result_block = block
                            local_stop_event.set()
                            return result_block
                    except:
                        pass
            
            # Če so vsi končali brez rezultata
            if all(ar.ready() for ar in async_results):
                break
            
            time.sleep(0.01)  # Kratka pavza
        
        return result_block
    
    finally:
        pool.terminate()
        pool.join()

class MiningServer:
    """Implementacija strežniške logike (Rank 0)."""
    
    def __init__(self, comm, size: int, config: dict):
        self.comm = comm
        self.num_workers = size - 1
        self.config = config
        self.received_data = deque()
        self.mqtt_listener: Optional[MqttListener] = None
        self.blockchain: Optional[Blockchain] = None
        
        self.current_difficulty = config['difficulty']
        self.blocks_mined = 0

    def setup(self):
        """Inicializacija blockchaina in MQTT."""
        self.blockchain = Blockchain(
            difficulty=self.current_difficulty,
            interval_generiranja_blokov=interval_generiranja_blokov,
            interval_popravka_tezavnosti=interval_popravka_tezavnosti
        )
        
        if self.config['use_mqtt']:
            self.mqtt_listener = MqttListener(
                topic=mqtt_topic, 
                data_queue=self.received_data, 
                logger=logger
            )
            self.mqtt_listener.start()
            self.received_data.append("Initial block data")

        self.log_start_info()

    def log_start_info(self):
        logger.info("\n[SERVER] Zacetek porazdeljenega rudarjenja")
        logger.info(f"[SERVER] Stevilo delavcev: {self.num_workers}")
        logger.info(f"[SERVER] Niti na delavca: {self.config['threads']}")
        logger.info(f"[SERVER] Skupno stevilo niti: {self.num_workers * self.config['threads']}")
        diff_type = "dinamicna" if self.config['dynamic_difficulty'] else "fiksna"
        logger.info(f"[SERVER] Tezavnost: {self.current_difficulty} ({diff_type})")
        logger.info(f"[SERVER] Cilj: {self.config['block_limit']} blokov")
        logger.info(f"[SERVER] MQTT: {'omogocen' if self.config['use_mqtt'] else 'onemogocen'}\n")

    def get_next_block_data(self, latest_index):
        if self.mqtt_listener and self.received_data:
            return self.received_data.popleft()
        return f"Block data {latest_index}"

    def broadcast_task(self, specific_worker=None):
        """Pošlje nalogo vsem delavcem ali samo enemu."""
        latest_block = self.blockchain.get_latest_block()
        data = self.get_next_block_data(latest_block.index + 1)
        
        task = TaskMessage(
            index=latest_block.index + 1,
            data=data,
            previous_hash=latest_block.hash,
            difficulty=self.current_difficulty,
            num_threads=self.config['threads']
        )
        
        if specific_worker:
            self.comm.send(task, dest=specific_worker, tag=TASK_TAG)
        else:
            for i in range(1, self.comm.Get_size()):
                self.comm.send(task, dest=i, tag=TASK_TAG)

    def handle_result(self, result_block, worker_rank):
        """Obdela prejet rezultat rudarjenja."""
        if self.blockchain.is_new_block_valid(result_block):
            self.blockchain.add_block(result_block)
            self.blocks_mined += 1
            print_block(result_block)
            
            if self.config['dynamic_difficulty']:
                self.blockchain.adjust_difficulty()
                if self.blockchain.difficulty != self.current_difficulty:
                    logger.info(f"[SERVER] Tezavnost spremenjena: {self.current_difficulty} -> {self.blockchain.difficulty}")
                    self.current_difficulty = self.blockchain.difficulty
            
            # Obvesti ostale delavce naj nehajo s trenutnim blokom
            for i in range(1, self.comm.Get_size()):
                if i != worker_rank:
                    self.comm.send(None, dest=i, tag=NEW_BLOCK_TAG)
            return True
        return False

    def run(self):
        self.setup()
        self.comm.Barrier() # Sinhronizacija z workerji
        self.broadcast_task() # Začetne naloge
        
        try:
            while self.blocks_mined < self.config['block_limit']:
                status = MPI.Status()
                result_block = self.comm.recv(source=MPI.ANY_SOURCE, tag=RESULT_TAG, status=status)
                worker_rank = status.Get_source()
                
                if result_block:
                    self.handle_result(result_block, worker_rank)
                
                if self.blocks_mined < self.config['block_limit']:
                    self.broadcast_task(specific_worker=worker_rank)
                    
        except Exception as e:
            logger.error(f"[SERVER] Napaka: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        if self.mqtt_listener:
            self.mqtt_listener.stop()
            
        for i in range(1, self.comm.Get_size()):
            try:
                self.comm.send(None, dest=i, tag=STOP_TAG)
            except:
                pass
                
        if self.config['show_stats']:
            stats(self.blockchain)


class MiningWorker:
    """Implementacija worker logike (Rank >= 1)."""
    
    def __init__(self, comm, rank: int):
        self.comm = comm
        self.rank = rank

    def check_signals(self):
        """Callback za preverjanje MPI signalov znotraj rudarjenja."""
        if self.comm.Iprobe(source=SERVER_RANK, tag=STOP_TAG):
            return True
        if self.comm.Iprobe(source=SERVER_RANK, tag=NEW_BLOCK_TAG):
            self.comm.recv(source=SERVER_RANK, tag=NEW_BLOCK_TAG)
            return True
        return False

    def run(self):
        logger.info(f"[WORKER {self.rank}] Pripravljen...")
        self.comm.Barrier()
        logger.info(f"[WORKER {self.rank}] Cakam na naloge...")
        
        try:
            while True:
                status = MPI.Status()
                self.comm.Probe(source=SERVER_RANK, status=status)
                tag = status.Get_tag()
                
                if tag == STOP_TAG:
                    self.comm.recv(source=SERVER_RANK, tag=STOP_TAG)
                    logger.info(f"[WORKER {self.rank}] Koncujem...")
                    break
                
                elif tag == NEW_BLOCK_TAG:
                    self.comm.recv(source=SERVER_RANK, tag=NEW_BLOCK_TAG)
                    continue
                
                elif tag == TASK_TAG:
                    task = self.comm.recv(source=SERVER_RANK, tag=TASK_TAG)
                    result = mine_block_multithread(task, self.rank, self.check_signals)
                    self.comm.send(result, dest=SERVER_RANK, tag=RESULT_TAG)
                    
        except Exception as e:
            logger.error(f"[WORKER {self.rank}] Napaka: {e}")


def run_mpi_mining():
    """Vstopna točka za MPI procese."""
    if MPI is None:
        print("NAPAKA: mpi4py ni naložen.")
        return

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    threads = num_threads if num_threads else multiprocessing.cpu_count()
    
    # Priprava konfiguracije
    if fixed_difficulty is None:
        diff = start_difficulty
        dynamic_diff = True
    else:
        diff = fixed_difficulty
        dynamic_diff = False
        
    config = {
        'difficulty': diff,
        'dynamic_difficulty': dynamic_diff,
        'block_limit': block_limit,
        'threads': threads,
        'use_mqtt': use_mqtt,
        'show_stats': show_stats
    }
    
    if size < 2:
        if rank == 0:
            logger.error("NAPAKA: Potrebna vsaj 2 procesa (1 server + 1 worker).")
        return
    
    if rank == SERVER_RANK:
        server = MiningServer(comm, size, config)
        server.run()
    else:
        worker = MiningWorker(comm, rank)
        worker.run()



def main():
    """Glavna funkcija programa."""
    try:
        from mpi4py import MPI
        comm = MPI.COMM_WORLD
        size = comm.Get_size()
        
        if size > 1:
            run_mpi_mining()
        else:
            n_procs = num_mpi_processes if num_mpi_processes else multiprocessing.cpu_count()
            print(f"Zaganjam MPI z {n_procs} procesi...")
            
            # Zaženi mpiexec
            script_path = os.path.abspath(__file__)
            cmd = ["mpiexec", "-n", str(n_procs), sys.executable, script_path]
            
            try:
                subprocess.run(cmd, check=True)
            except FileNotFoundError:
                print("NAPAKA: mpiexec ni najden. Namesti MS-MPI ali uporabi:")
                print(f"  mpiexec -n {n_procs} python {script_path}")
            except subprocess.CalledProcessError as e:
                print(f"NAPAKA pri zagonu MPI: {e}")
    
    except ImportError:
        print("NAPAKA: mpi4py ni nameščen. Namesti z: pip install mpi4py")

if __name__ == "__main__":
    main()
