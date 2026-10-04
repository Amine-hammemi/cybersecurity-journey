import socket
import sys
import time 

def check_port(target_ip: str, port: int, timeout: float = 1.0 ) -> str:
    """
    Attempts a TCP connection to a single port.
    Returns 'open', 'closed' or 'filtered'
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    result = sock.connect_ex((target_ip, port))
    sock.close()

    if result == 0: 
        return "open"
    elif result == 111: # Econnrefused on linux
        return "closed"
    else:
        return "filtered"

def scan_range(target_ip: str, start_port: int, end_port: int ,timeout: float = 1.0) :
    """
    scans a range of ports sequentially and returns a list of (port, state) tuple.
    """

    results = []
    for port in range( start_port, end_port +1):
        state = check_port(target_ip , port , timeout)
        results.append((port, state))
    return results

if __name__ == "__main__":
    target = sys.argv[1]
    start_port = int(sys.argv[2])
    end_port = int(sys.argv[3])

    start_time = time.time()
    results = scan_range(target, start_port, end_port)
    elapsed = time.time() - start_time

    for port, state in results:
        if state == "open" or state == "filtered": # only print open ports by default, like nmap's default behavior
            print (f"{target}:{port} -> {state}")


    open_count = sum(1 for _, state in results if state == "open")
    print(f"Scanned {end_port - start_port +1} ports in {elapsed:.2f}s - {open_count} open ports found.")