#!/bin/python
import bluetooth
import sys
import threading
import select
import subprocess

DEBUG=True
CONNECTED_MESSAGE = "[CONNECTED]"
DISCONNECTED_MESSAGE = "[DISCONNECTED]"
TIMEOUT = 1

disconnect_event = threading.Event()

def debug_message(message: str): 
    '''
    Print debug message.
    '''
    if DEBUG: 
        print(message)

def main(args: list[str]): 
    '''
    Entry point.
    '''

    name = args[1] 
    uuid = args[2]

    # attempt to run again in the case of a crash, except for Keyboard Interrupt
    while True: 
        try: 
            run_server(name, uuid) 
        except KeyboardInterrupt: 
            break
        except Exception as e:
            debug_message(str(e))

def run_server(name: str, uuid: str): 
    '''
    Run the server.
    '''
    print(DISCONNECTED_MESSAGE, flush=True)

    # make device discoverable
    subprocess.run(["bluetoothctl", "discoverable", "on"])
        
    debug_message("Starting server.")
    listener_sock = create_socket()
    listen_and_advertise(listener_sock, name, uuid)
    debug_message("Listening.")

    # connect and start send/receive threads, retry if connection lost
    while True:
        try:
            debug_message("Waiting for client.")
            client_sock, _ = wait_for_connection(listener_sock)
            print(CONNECTED_MESSAGE, flush=True)
            debug_message("client connected")

            client_sock.settimeout(TIMEOUT)
        
            recv_thread = threading.Thread(target=receive_loop, args=(client_sock,), daemon=True)
            send_thread = threading.Thread(target=send_loop, args=(client_sock,), daemon=True)

            recv_thread.start() 
            send_thread.start()

            recv_thread.join() 
            send_thread.join()
            disconnect_event.clear()

            client_sock.close() 
            print(DISCONNECTED_MESSAGE, flush=True)
            debug_message("client disconnected")
        except KeyboardInterrupt as e: 
            raise e
        except bluetooth.BluetoothError: 
            break
        except: 
            continue

    listener_sock.close()

def create_socket() -> bluetooth.BluetoothSocket: 
    '''
    Create the socket.
    '''
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", bluetooth.PORT_ANY)) 
    return server_sock

def listen_and_advertise(server_sock: bluetooth.BluetoothSocket, name: str, uuid: str): 
    '''
    Start listening, and advertise the server.
    '''
    server_sock.listen(1)
    bluetooth.advertise_service(server_sock, name, service_id=uuid, service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS], profiles=[bluetooth.SERIAL_PORT_PROFILE])

def wait_for_connection(server_sock: bluetooth.BluetoothSocket): 
    '''
    Wait for a connection.
    '''
    client_sock, client_info = server_sock.accept() 
    return client_sock, client_info

def send_loop(client_sock: bluetooth.BluetoothSocket): 
    '''
    Continuous send loop.
    '''
    while True: 
        if disconnect_event.is_set(): 
            break
        ready, _, _ = select.select([sys.stdin], [], [], TIMEOUT)
        if not ready:
            continue

        line = sys.stdin.readline()
        try: 
            client_sock.send(line.encode())
        except: 
            disconnect_event.set()
            break

def receive_loop(client_sock: bluetooth.BluetoothSocket): 
    '''
    Continuous receive loop.
    '''
    while True: 
        if disconnect_event.is_set(): 
            break
        try:
            data = client_sock.recv(1024)
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
        except Exception as e: 
            disconnect_event.set()
            break

if __name__ == "__main__": 
    main(sys.argv)
