import sys
import socket
import getopt
import threading
import subprocess
import time

# GLOBAL VARIABLES
listen = False
command = False
upload = False
execute = ""
target = ""
upload_destination = ""
port = 0
interactive = False
users_cnt = 0

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
    print(bcolors.TITLE + "                         Awesome Net Tool                          " + bcolors.ENDC)

def usage():
    print('\n                              ' + bcolors.UNDERLINE + "USAGE\n" + bcolors.ENDC)
    print('-l--listen              - listen on [host]:[port] for incomming connections')
    print('-e--execute=file_to_run - execute the given file upon receiving a connection')
    print('-c--command             - initialize a command shell')
    print('-u --upload=destination - upon receiving connection upload a file and write')
    print('                          to [destination]')
    print('-i--interactive         - initates terminal operation')
    sys.exit()

def showError(err):
    print(bcolors.FAIL + '[*] Error: ' + str(err) + bcolors.ENDC)
    print(bcolors.BOLD + 'Stopping work...' + bcolors.ENDC)
    sys.exit(2)

def successExit():
    print(bcolors.BOLD + 'Thank you for work! Bye!')
    sys.exit()

def clientSender(buffer):
    global interactive
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(bcolors.OKGREEN + 'Connecting...' + bcolors.ENDC)
        client.connect((target, port))

        while True:
            if len(buffer):
                client.send(bytes(buffer, 'utf-8'))
                if not interactive:
                    if buffer in ("[%~escape~%]", "[%~escape~%]\n"):
                        successExit()
                    print(bcolors.OKGREEN + 'Sending buffer...' + bcolors.ENDC)

            recvLen = 1024
            response = ""

            if not interactive:
                print(bcolors.OKGREEN + 'Getting response...' + bcolors.ENDC)
                print(bcolors.BOLD + 'Progress', end='')
            while recvLen >= 1024:
                if not interactive:
                    print(bcolors.BOLD + '.', end='')
                data = client.recv(1024)
                recvLen = len(data)
                response += str(data, 'utf-8')
            if "[%~escape~%]" in response:
                print(response.replace("[%~escape~%]", ''))
                successExit()
            if not interactive:
                print(bcolors.BOLD + 'Done' + bcolors.ENDC)
                print(response)
                print(bcolors.OKBLUE + 'You can send more data ([%~escape~%], CTRL-D to send): ' + bcolors.ENDC)
            else:
                print(response, end='')

            # wait for more input
            if interactive:
                try:
                    buffer = input()
                except EOFError:
                    client.send(bytes('exit\n', 'utf-8'))
                    client.close()
                    print()
                    successExit()
                buffer += '\n'
            else:
                buffer = sys.stdin.read()

    except Exception as e:
        client.close()
        showError(e)

def serverLoop():
    global target, users_cnt

    if not len(target):
        target = "0.0.0.0"

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((target, port))
        server.listen(5)
        print(bcolors.OKGREEN + 'Server starts on port %d'% port)
    except Exception as ex:
        showError(ex)

    while True:
        client_socket, addr = server.accept()
        users_cnt += 1
        print(bcolors.OKBLUE + 'Received incoming connection from %s:%d' % (addr[0], addr[1]))
        print(bcolors.BOLD + 'There are %s users now' % users_cnt + bcolors.ENDC)
        client_thread = threading.Thread(target=clientHandler, args=(client_socket, addr,))
        client_thread.start()

def clientHandler(client_socket, addr):
    global upload, execute, command, upload_destination, users_cnt
    # check for upload file
    if len(upload_destination):
        file_buffer = bytes()

        while True:
            data = client_socket.recv(1024)
            file_buffer += data
            if len(data) < 1024:
                break

        try:
            file_descriptor = open(upload_destination, "wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()

            response = "Successfully saved file to %s\r\n" % upload_destination
        except:
            response = "Failed to save file to %s\r\n" % upload_destination
        if not execute and not command:
            response += "[%~escape~%]"
        client_socket.send(bytes(response, 'utf-8'))

    # check for execution
    if len(execute):
        output = runCommand(execute)

        if not command:
            output += bytes("[%~escape~%]")

        client_socket.send(output)

    if command:
        try:
            client_socket.send(bytes("<ISYN_NB:#> ", 'utf-8'))
            while True:
                cmd_buffer = str()
                while ('\n' not in cmd_buffer):
                    cmd_buffer += str(client_socket.recv(1024), 'utf-8')
                if cmd_buffer == 'exit\n':
                    client_socket.send(bytes("[%~escape~%]", 'utf-8'))
                    break
                output = runCommand(cmd_buffer)
                if type(output) == str:
                    response = bytes(output + "\n<ISYN_NB:#> ", 'utf-8')
                else:
                    response = bytes(str(output, 'utf-8') + "\n<ISYN_NB:#> ", 'utf-8')
                client_socket.send(response)
        except ConnectionResetError:
            print(bcolors.OKBLUE + 'Connection was closed by user' + bcolors.ENDC)
        except Exception as e:
            showError(e)

    users_cnt -= 1
    print(bcolors.OKBLUE + 'Connection stopped with %s:%d' % (addr[0], addr[1]))
    print(bcolors.BOLD + 'There are %s users now' % users_cnt + bcolors.ENDC)

def runCommand(command):
    command = command.rstrip()
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except:
        output = "Filed to execute command\r\n"
    return output

def main():
    showLogo()
    global listen, port, execute, command, upload_destination, target, interactive

    if not len(sys.argv[1:]):
        usage()

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:ciu:",
            ["help", "listen", "execute", "target", "port", "command", "interactive", "upload"])
    except getopt.GetoptError as err:
            showError(err)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command", "--commandshell"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ('-i', '--interactive'):
            interactive = True
        elif o in ("-p", "--port"):
            try:
                port = int(a)
            except ValueError as err:
                showError(err)
        else:
            showError(o + '- not such option')

    if not listen and len(target) and port > 0:
        buffer = str()
        if not interactive:
            print(bcolors.OKBLUE + 'Input your data: ' + bcolors.ENDC)
            buffer = sys.stdin.read()
        clientSender(buffer)
    if listen:
        serverLoop()

main()