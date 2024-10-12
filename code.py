from math import log2
from colorama import Fore, Style
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate

tracefiles = ['TraceFiles/gcc.trace', 'TraceFiles/gzip.trace', 'TraceFiles/mcf.trace', 'TraceFiles/swim.trace', 'TraceFiles/twolf.trace'] 

class Cache:
    """
    A class representing a Cache memory structure with configurable cache size, block size, 
    and associativity. The cache uses an LRU (Least Recently Used) replacement policy and
    handles read requests to check for cache hits and misses.
    """
    def __init__(self, cache_size: int, block_size: int, associativity: int):
        """
        Initialize the cache with given size, block size, and associativity. Calculate 
        the number of index bits, offset bits, and tag bits based on the configuration.
        
        Args:
            cache_size (int): Total size of the cache in bytes.
            block_size (int): Size of each cache block in bytes.
            associativity (int): Cache associativity (number of blocks per set).
        """
        self.cache_size = cache_size
        self.block_size = block_size
        self.associativity = associativity
        self.sets = cache_size//(block_size*associativity)
        self.no_of_ind_bits = int(log2(self.sets))
        self.no_of_offset_bits = int(log2(self.block_size))
        self.no_of_tag_bits = 32 - self.no_of_ind_bits - self.no_of_offset_bits
        self.hit_count = 0
        self.miss_count = 0
        self.cache = [[Block('0'*self.no_of_tag_bits, False) for i in range(self.associativity)] for j in range(self.sets)]

    def check(self, address: str):
        """
        Check if the given address is present in the cache.
        
        Args:
            address (str): The binary address from the processor.

        Returns:
            bool: True if the address is found in the cache (hit), False otherwise (miss).
        """
        index = self.extract_index(address)
        tag = self.extract_tag(address)
        offset = self.extract_offset(address)
        for block in self.cache[index]:
            if block.tag == tag and block.valid:
                self.hit_count += 1
                self.lru_handling(index, True, block.lru_counter)
                return True
        self.miss_count += 1
        self.evictor(index, tag, offset)
        self.lru_handling(index, False)
        return False

    def extract_index(self, address: str):
        """
        Extract the index from the binary address.
        
        Args:
            address (str): Binary address of the memory access.
        
        Returns:
            int: Extracted index value.
        """
        index_bits = address[self.no_of_tag_bits: self.no_of_tag_bits + self.no_of_ind_bits]
        return int(index_bits, 2)

    def extract_tag(self, address: str):
        """
        Extract the tag from the binary address.
        
        Args:
            address (str): Binary address of the memory access.
        
        Returns:
            str: Extracted tag bits.
        """
        tag_bits = address[:self.no_of_tag_bits]
        return tag_bits

    def extract_offset(self, address: str):
        """
        Extract the offset from the binary address.
        
        Args:
            address (str): Binary address of the memory access.
        
        Returns:
            int: Extracted offset value.
        """
        offset_bits = address[-self.no_of_offset_bits:]
        return int(offset_bits, 2)

    def lru_handling(self, set_index: int, hit: bool, cur: int=None):
        """
        Update the LRU counters for the cache blocks in a set based on whether the access 
        was a hit or miss. If hit, adjust the LRU position for the accessed block.
        
        Args:
            set_index (int): The index of the cache set being accessed.
            hit (bool): True if the access was a hit, False otherwise.
            cur (int, optional): The current LRU counter of the hit block (only used for hit).
        """
        if hit:
            for block in self.cache[set_index]:
                if block.lru_counter > cur:
                    block.lru_counter -= 1
                elif block.lru_counter == cur:
                    block.lru_counter = self.associativity - 1
        else:
            for block in self.cache[set_index]:
                block.lru_counter -= 1

    def evictor(self, set_index: int, tag: str, offset: str):
        """
        Evict the least recently used block from a cache set if no empty blocks are available.
        Otherwise, allocate a free block for the new tag.
        
        Args:
            set_index (int): The index of the set where eviction or block placement occurs.
            tag (str): The tag to be placed in the cache block.
            offset (str): Offset from the address (not used here but included for future use).
        """
        for block in self.cache[set_index]:
            if not block.valid:
                block.tag = tag
                block.valid = True
                block.lru_counter = self.associativity
                return 
        for block in self.cache[set_index]:
            if block.lru_counter == 0:
                block.tag = tag
                block.valid = True
                block.lru_counter = self.associativity
                return

class Block:
    """
    A class representing a cache block. It stores the tag, validity, and the LRU counter 
    used for LRU replacement policy.
    """
    def __init__(self, tag: str, valid: bool, lru_counter: int=-1):
        """
        Initialize a block with a tag, valid bit, and LRU counter.

        Args:
            tag (str): The tag of the block.
            valid (bool): The validity of the block (True if the block contains valid data).
            lru_counter (int, optional): The current LRU counter value.
        """
        self.tag = tag
        self.valid = valid
        self.data = "0"*32
        self.lru_counter = lru_counter

def plot(x_label, y_label,title, dfs, filename):
    """
    Plot the dataframes' values and generate graphs for comparison between tracefiles.
    
    Args:
        x_label (str): Label for the x-axis of the plot.
        y_label (str): Label for the y-axis of the plot.
        title (str): The title of the plot.
        dfs (list): List of dataframes containing the data to be plotted.
        filename (str): Filename for saving the plot.
    """
    for i, df in enumerate(dfs):
        plt.plot(df[x_label], df[y_label], label = tracefiles[i],marker='o')    
    plt.grid(True)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend()
    plt.savefig(filename)
    plt.show()

def hextobin(address):
    """
    Convert a hexadecimal address into a 32-bit binary string.
    
    Args:
        address (str): The hexadecimal address to be converted.
    
    Returns:
        str: A 32-bit binary string representation of the address.
    """
    num=str(bin(int(address,base=16)))
    num=num[2:]
    return num.zfill(32)

def parta():
    """
    Part A: Simulate cache behavior for different tracefiles and display hit/miss rates
    for each tracefile with a fixed cache size, block size, and associativity.
    """
    cache_size = 1024 * 1024  
    block_size = 4  
    associativity = 4  
    for tracefile in tracefiles:
        cache1 = Cache(cache_size, block_size, associativity)
        with open(tracefile, 'r') as file:
            for line in file:
                address_hex = line.split()[1][2:]
                address_bin = hextobin(address_hex)
                cache1.check(address_bin)
        hit_rate = cache1.hit_count / (cache1.hit_count + cache1.miss_count)
        miss_rate = cache1.miss_count / (cache1.hit_count + cache1.miss_count)
        print(f'{Fore.GREEN}Hit Rate{Style.RESET_ALL} for {Fore.CYAN}{tracefile}{Style.RESET_ALL}: {Fore.GREEN}{hit_rate * 100:.6f}%{Style.RESET_ALL}')
        print(f'{Fore.RED}Miss Rate{Style.RESET_ALL} for {Fore.CYAN}{tracefile}{Style.RESET_ALL}: {Fore.RED}{miss_rate * 100:.6f}%{Style.RESET_ALL}')
        print()


def partb():
    """
    Part B: Vary the cache size and measure the hit/miss rates for different cache sizes
    across multiple tracefiles. The results are displayed and plotted.
    """
    dfs = []
    cache_sizes = [1024 * 2 ** i for i in range(7, 12 + 1)]
    cache_sizes_kb = [i // 1024 for i in cache_sizes]
    with pd.ExcelWriter('Changing_CacheSize.xlsx', engine='openpyxl') as writer:
        for tracefile in tracefiles:
            hit_rates = []
            miss_rates = []
            hit_counts = []
            miss_counts = []

            for cache_size in cache_sizes:
                cache1 = Cache(cache_size, 4, 4)
                with open(tracefile, 'r') as file:
                    for line in file:
                        address_hex = line.split()[1][2:]
                        address_bin = hextobin(address_hex)
                        cache1.check(address_bin)

                hit_rates.append((cache1.hit_count / (cache1.hit_count + cache1.miss_count)) * 100)
                miss_rates.append((cache1.miss_count / (cache1.hit_count + cache1.miss_count)) * 100)
                hit_counts.append(cache1.hit_count)
                miss_counts.append(cache1.miss_count)

            df = pd.DataFrame({
                'Cache Size (in kb)': cache_sizes_kb,
                'Hit count': hit_counts,
                'Miss count': miss_counts,
                'Hit Rate': hit_rates,
                'Miss Rate': miss_rates
            })
            df.to_excel(writer, sheet_name=tracefile.split('.')[0], index=False)

            print(tracefile)
            print()
            temp_df = pd.DataFrame({
                'Cache Size (in kb)': [f"{Fore.LIGHTBLUE_EX}{size}{Style.RESET_ALL}" for size in cache_sizes_kb],
                'Hit count': [f"{Fore.GREEN}{hit}{Style.RESET_ALL}" for hit in hit_counts],
                'Miss count': [f"{Fore.RED}{miss}{Style.RESET_ALL}" for miss in miss_counts],
                'Hit Rate': [f"{Fore.GREEN}{hit_rate:.6f}{Style.RESET_ALL}" for hit_rate in hit_rates],
                'Miss Rate': [f"{Fore.RED}{miss_rate:.6f}{Style.RESET_ALL}" for miss_rate in miss_rates]
            })
            print(tabulate(temp_df, headers='keys', tablefmt="grid"))
            print()
            dfs.append(df)

    plot('Cache Size (in kb)', 'Miss Rate', "Cache Size vs Miss Rate", dfs, "Cache Size vs Miss Rate")


def partc():
    """
    Part C: Vary the block size and measure the hit/miss rates for different block sizes
    across multiple tracefiles. The results are displayed and plotted.
    """
    dfs=[]
    cache_size = 1024 * 1024
    block_sizes = [2 ** i for i in range(0, 7 + 1)]
    with pd.ExcelWriter('Changing_BlockSize.xlsx', engine='openpyxl') as writer:
        for tracefile in tracefiles:
            hit_rates = []
            miss_rates = []
            hit_counts = []
            miss_counts = []
            for block_size in block_sizes:
                cache1 = Cache(cache_size, block_size, 4)
                with open(tracefile, 'r') as file:
                    for line in file:
                        address_hex = line.split()[1][2:]
                        address_bin = hextobin(address_hex)
                        cache1.check(address_bin)

                hit_rates.append((cache1.hit_count / (cache1.hit_count + cache1.miss_count))*100)
                miss_rates.append((cache1.miss_count / (cache1.hit_count + cache1.miss_count))*100)
                hit_counts.append(cache1.hit_count)
                miss_counts.append(cache1.miss_count)

            df = pd.DataFrame({'Block Size': block_sizes, 'Hit count': hit_counts, 'Miss count': miss_counts, 'Hit Rate': hit_rates, 'Miss Rate': miss_rates})
            df.to_excel(writer, sheet_name=tracefile.split('.')[0], index=False)
            temp_df = pd.DataFrame({
                'Block Size': [f"{Fore.LIGHTBLUE_EX}{block_size}{Style.RESET_ALL}" for block_size in block_sizes],
                'Hit count': [f"{Fore.GREEN}{hit}{Style.RESET_ALL}" for hit in hit_counts],
                'Miss count': [f"{Fore.RED}{miss}{Style.RESET_ALL}" for miss in miss_counts],
                'Hit Rate': [f"{Fore.GREEN}{hit_rate:.6f}{Style.RESET_ALL}" for hit_rate in hit_rates],
                'Miss Rate': [f"{Fore.RED}{miss_rate:.6f}{Style.RESET_ALL}" for miss_rate in miss_rates]
            })

            print(tracefile)
            print()
            print(tabulate(temp_df, headers='keys',tablefmt="grid"))
            print()
            dfs.append(df)

    plot('Block Size', 'Miss Rate','Block Size vs Miss Rate', dfs, 'Block Size vs Miss Rate')


def partd():
    """
    Part D: Vary the associativity and measure the hit/miss rates for different associativities
    across multiple tracefiles. The results are displayed and plotted.
    """
    dfs = []
    cache_size = 1024 * 1024
    block_size = 4
    associativities = [2 ** i for i in range(0, 6 + 1)]
    with pd.ExcelWriter('Changing_Associativity.xlsx', engine='openpyxl') as writer:
        for tracefile in tracefiles:
            hit_rates = []
            miss_rates = []
            hit_counts = []
            miss_counts = []
            for associativity in associativities:
                cache1 = Cache(cache_size, block_size, associativity)
                with open(tracefile, 'r') as file:
                    for line in file:
                        address_hex = line.split()[1][2:]
                        address_bin = hextobin(address_hex)
                        cache1.check(address_bin)

                hit_rates.append((cache1.hit_count / (cache1.hit_count + cache1.miss_count))*100)
                miss_rates.append((cache1.miss_count / (cache1.hit_count + cache1.miss_count))*100)
                hit_counts.append(cache1.hit_count)
                miss_counts.append(cache1.miss_count)

            df = pd.DataFrame({'Associativity': associativities, 'Hit count': hit_counts, 'Miss count': miss_counts, 'Hit Rate': hit_rates, 'Miss Rate': miss_rates})
            df.to_excel(writer, sheet_name=tracefile.split('.')[0], index=False)
            temp_df = pd.DataFrame({
                'Associativity': [f"{Fore.LIGHTBLUE_EX}{assoc}{Style.RESET_ALL}" for assoc in associativities],
                'Hit count': [f"{Fore.GREEN}{hit}{Style.RESET_ALL}" for hit in hit_counts],
                'Miss count': [f"{Fore.RED}{miss}{Style.RESET_ALL}" for miss in miss_counts],
                'Hit Rate': [f"{Fore.GREEN}{hit_rate:.6f}{Style.RESET_ALL}" for hit_rate in hit_rates],
                'Miss Rate': [f"{Fore.RED}{miss_rate:.6f}{Style.RESET_ALL}" for miss_rate in miss_rates]
            })
            print(tracefile)
            print()
            print(tabulate(temp_df, headers='keys',tablefmt="grid")+"\n")
            print()
            dfs.append(df)
    plot('Associativity', 'Hit Rate','Associativity vs Hit Rate', dfs,'Associativity vs Hit Rate')
        

def main():
    """
    Main function to display the menu and handle user input for the cache simulation.
    """
    print(Fore.CYAN + "Cache Simulation" + Style.RESET_ALL)
    
    while True:
        print(Fore.BLUE + "\nOptions:\n" +
              "1. Part A: Analyze cache simulation with fixed cache size, block size, and associativity\n" +
              "2. Part B: Analyze cache performance with varying cache sizes\n" +
              "3. Part C: Analyze cache performance with varying block sizes\n" +
              "4. Part D: Analyze cache performance with varying associativities\n" +
              "-1. Exit" + Style.RESET_ALL)
        
        choice = input(Fore.LIGHTYELLOW_EX + "Please enter your choice: " + Style.RESET_ALL).strip()
        
        match choice:
            case '1':
                parta()
            case '2':
                partb()
            case '3':
                partc()
            case '4':
                partd()
            case '-1':
                print(Fore.RED + "Exiting..." + Style.RESET_ALL)
                break
            case _:
                print(Fore.RED + "Invalid choice. Please enter a number between 1 and 4, or -1 to exit." + Style.RESET_ALL)
                continue

if __name__ == "__main__":
    main()
