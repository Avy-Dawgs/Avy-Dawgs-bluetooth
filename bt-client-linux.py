#!/bin/python
import sys
import bluetooth
import threading
import select

DEBUG = True
CONNECTED_MESSAGE = "[CONNECTED]"
DISCONNECTED_MESSAGE = "[DISCONNECTED]"
TIMEOUT = 1

disconnect_event = threading.Event()


def debug_message(message: str): 
    if DEBUG: 
        print(message)

def main(args: list[str]): 

    name = args[1] 
    uuid = args[2] 
    addr = args[3]

    while True:
        try:
            run_client(name, uuid, addr)
        except KeyboardInterrupt: 
            break
        except Exception as e: 
            debug_message(str(e))

def run_client(name: str, uuid: str, addr: str): 
    print(DISCONNECTED_MESSAGE, flush=True)

    debug_message("Starting client.")

    while True:
        service_matches = bluetooth.find_service(name=name, uuid=uuid, address=addr) 

        if len(service_matches) == 0: 
            debug_message("Couldn't find server.")
            continue
        elif len(service_matches) > 1: 
            debug_message("More than one server found.")
            continue

        first_match = service_matches[0]
        port = first_match["port"]
        name = first_match["name"]
        host = first_match["host"]

        debug_message(f"Found server name \"{name}\" on host {host}")

        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        debug_message("Created socket.")

        sock.connect((host, port))
        print(CONNECTED_MESSAGE, flush=True)
        debug_message("Connected to server.")

        sock.settimeout(TIMEOUT)

        recv_thread = threading.Thread(target=receive_loop, args=(sock,), daemon=True)
        send_thread = threading.Thread(target=send_loop, args=(sock,), daemon=True)

        recv_thread.start() 
        send_thread.start()

        recv_thread.join()
        send_thread.join()
        disconnect_event.clear()

        sock.close()
        print(DISCONNECTED_MESSAGE, flush=True)
        debug_message("Connection closed.")

def send_loop(sock: bluetooth.BluetoothSocket): 
    while True:
        if disconnect_event.is_set(): 
            break
        ready, _, _ = select.select([sys.stdin], [], [], TIMEOUT)
        if not ready:
            continue

        line = sys.stdin.readline()
        try: 
            sock.send(line.encode())
        except:
            disconnect_event.set()
            break

def receive_loop(sock: bluetooth.BluetoothSocket): 
    while True: 
        if disconnect_event.is_set(): 
            break
        try:
            data = sock.recv(1024)
            if not data: 
                disconnect_event.set()
                break
            print(data, flush=True)
        except bluetooth.BluetoothError as e:
            if "timed out" in str(e): 
                continue
            else:  
                disconnect_event.set() 
                break
        except: 
            disconnect_event.set()
            break

if __name__ == "__main__": 
    main(sys.argv)
