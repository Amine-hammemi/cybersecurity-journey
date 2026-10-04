import socket
import sys

def check_port(target_ip:str , port:int, timeout:float =2.0) ->str :
    """
    Attempts a TCP connection to a single port.
    Returns 'open','closed',or 'filtered'
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    result = sock.connect_ex((target_ip , port))
    sock.close()

    if result == 0:
        return 'open'
    elif result == 111: # Econnrefused on linux
        return 'closed'
    else:
        return 'filtered'

if __name__ == "__main__":
    target = sys.argv[1]
    port = int(sys.argv[2])
    state = check_port(target, port)
    print(f"{target}:{port} -> {state}")