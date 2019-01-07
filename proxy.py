import sys
import socket
import threading
import getopt

TIMEOUT = 3
HEXDUMP = False

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    TITLE = '\033[1;30;41m'

def showLogo():
    print(bcolors.HEADER + " ___ ______   ___   _   ____         __ _                          " + bcolors.ENDC)
    print(bcolors.HEADER + "|_ _/ ___\ \ / / \ | | / ___|  ___  / _| |___      ____ _ _ __ ___ " + bcolors.ENDC)
    print(bcolors.HEADER + " | |\___ \\\\ V /|  \| | \___ \ / _ \| |_| __\ \ /\ / / _` | '__/ _ \\" + bcolors.ENDC)
    print(bcolors.HEADER + " | | ___) || | | |\  |  ___) | (_) |  _| |_ \ V  V / (_| | | |  __/" + bcolors.ENDC)
    print(bcolors.HEADER + "|___|____/ |_| |_| \_| |____/ \___/|_|  \__| \_/\_/ \__,_|_|  \___|" + bcolors.ENDC)
    print(bcolors.TITLE + "                               PROXY                                " + bcolors.ENDC)

def usage():
    print('\n                              ' + bcolors.UNDERLINE + "USAGE\n" + bcolors.ENDC)

def server_loop(lHost, lPort, rHost, rPort, receive_first):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server.bind((lHost, lPort))
    except:
        print(bcolors.FAIL + '[!!] Failed to listen on %s:%d ' % (lHost, lPort) + bcolors.ENDC)
        print(bcolors.BOLD + 'Check for other listening sockets or correct permissions' + bcolors.ENDC)
        sys.exit(0)

    server.listen(5)
    print(bcolors.OKGREEN + 'Listening on %s:%d' % (lHost, lPort) + bcolors.ENDC)

    while True:
        client_socket, addr = server.accept()
        print(bcolors.OKBLUE + '[<==] Receiving incoming connection from %s:%d' % (addr[0], addr[1]) + bcolors.ENDC)

        proxy_thread = threading.Thread(target=proxy_handler, args=(client_socket, rHost, rPort, receive_first))
        proxy_thread.start()

def proxy_handler(client_socket, rHost, rPort, receive_first):
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remote_socket.connect((rHost, rPort))

    if receive_first:
        remote_buffer = receive_from(remote_socket)
        print(hexdump(bytes(remote_buffer, 'utf-8', errors='ignore')))

        remote_buffer = response_handler(remote_buffer)

        if len(remote_buffer):
            print(bcolors.OKBLUE + '[==>] Sending %d bytes to localhost' % len(remote_buffer) + bcolors.ENDC)
            client_socket.send(bytes(remote_buffer, 'utf-8', errors='ignore'))

    while True:
        local_buffer = receive_from(client_socket)
        if len(local_buffer):
            print(bcolors.OKBLUE + '[<==] Received %d bytes from localhost' % len(local_buffer) + bcolors.ENDC)
            print(hexdump(bytes(local_buffer, 'utf-8')))

            local_buffer = request_handler(bytes(local_buffer, 'utf-8', errors='ignore'))
            remote_socket.send(local_buffer)
            print(bcolors.OKBLUE + '[==>] Sent to remote')

        remote_buffer = receive_from(remote_socket)
        if len(remote_buffer):
            print(bcolors.OKBLUE + '[<==] Received %d byted from remote' % len(remote_buffer) + bcolors.ENDC)
            print(hexdump(bytes(remote_buffer, 'utf-8', errors='ignore')))

            remote_buffer = response_handler(remote_buffer)
            client_socket.send(bytes(remote_buffer, 'utf-8', errors='ignore'))

            print(bcolors.OKBLUE + '[==>] Sent to localhost' + bcolors.ENDC)
        if not len(local_buffer) or not len(remote_buffer):
            client_socket.close()
            remote_socket.close()
            print(bcolors.WARNING + 'Connections closed because there are no more data' + bcolors.ENDC)
            break

def receive_from(connection):
    buffer = ""
    connection.settimeout(TIMEOUT)

    try:
        while True:
            data = connection.recv(1024)
            buffer += str(data, 'utf-8', errors='ignore')
            if len(data) < 1024:
                break
    except Exception as ex:
        print(bcolors.WARNING + '[!] Error when receive data {' + str(ex) + '}' + bcolors.ENDC)

    return buffer

def request_handler(buffer):
    #
    #       Here you can modify traffic
    #
    return buffer

def response_handler(buffer):
    #
    #       Here you can modify traffic
    #
    return buffer

def hexdump(src, length=16):
    global HEXDUMP
    if not HEXDUMP:
        return ''
    result = []
    digits = 4 if isinstance(src, str) else 2
    for i in range(0, len(src), length):
        s = src[i:i+length]
        hexa = ' '.join(map('{0:0>2X}'.format, s))
        text = ''.join([chr(x) if 0x20 <= x < 0x7F else '.' for x in s])
        result.append('%04X   %-*s   %s' % (i, length * (digits + 1), hexa, text))
    return '\n'.join(result)

def main():
    global TIMEOUT, HEXDUMP
    showLogo()

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'l:p:r:q:ft:h',
                        ['localHost', 'localPort', 'remoteHost', 'remotePort', 'recieve_first', 'timeout', 'hexdump'])
    except getopt.GetoptError as err:
        print(bcolors.FAIL + '[!!] ' + str(err) + bcolors.ENDC)
        usage()


    localHost, remoteHost = 'localhost', 'localhost'
    localPort, remotePort = 0, 0
    receive_first = False

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-l', '--localHost'):
            localHost = a
        elif o in ('-p', '--localPort'):
            try:
                localPort = int(a)
            except ValueError as err:
                print(bcolors.FAIL + '           [!!!] Local port must be a number value (' + str(err) + ')' + bcolors.ENDC)
                sys.exit(2)
        elif o in ('-r', '--remoteHost'):
            remoteHost = a
        elif o in ('-q', '--remotePort'):
            try:
                remotePort = int(a)
            except ValueError as err:
                print(bcolors.FAIL + '           [!!!] Local port must be a number value (' + str(err) + ')' + bcolors.ENDC)
                sys.exit(2)
        elif o in ('-f', '--receive-first'):
            receive_first = True
        elif o in ('-t', '--time-out'):
            try:
                TIMEOUT = int(a)
            except ValueError as err:
                print(bcolors.FAIL + '           [!!!] Timeout must be a number value (' + str(err) + ')' + bcolors.ENDC)
                sys.exit(2)
        elif o in ('-h', '--hexdump'):
            HEXDUMP = True

    if not localPort or not localHost or not remoteHost or not remotePort:
        print(bcolors.FAIL + '           [!!!] You must set all required variables' + bcolors.ENDC)
        usage()
        sys.exit(0)

    server_loop(localHost, localPort, remoteHost, remotePort, receive_first)

main()