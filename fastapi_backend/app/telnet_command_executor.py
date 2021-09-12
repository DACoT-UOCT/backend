import sys
import time
import queue
import struct
import telnetlib
from telnetlib import DO, DONT, IAC, WILL, WONT, NAWS, SB, SE

class TelnetCommandExecutor:
    def __init__(self, host, port=23, connection_timeout=40, logger=None):
        self.__logger = logger
        self.__commands = queue.Queue()
        self.__target_host = host
        self.__target_port = port
        self.__conn_timeout = connection_timeout
        self.__reads_outputs = {}
        self.__command_history = []
        self.__current_command = "init"

    def __log_print(self, msg):
        if self.__logger:
            self.__logger.debug(msg)
        else:
            print(msg)

    def command(self, identifier, command):
        self.__command_history.append(identifier)
        item = (identifier, lambda **kwargs: self.__command_impl(command, **kwargs))
        self.__commands.put(item)

    def exit_interactive_command(self, cmd_name='exit-interactive'):
        self.command(cmd_name, '-\n\n')

    def sleep(self, seconds):
        item = ("sleep", lambda **kwargs: time.sleep(seconds))
        self.__commands.put(item)

    def read_lines(self, encoding="ascii", line_ending=b"\n"):
        item = (
            "read_lines",
            lambda **kwargs: self.__read_lines_impl(encoding, line_ending, **kwargs),
        )
        self.__commands.put(item)

    def read_until(self, text, timeout=0, encoding="ascii"):
        item = (
            "read_until",
            lambda **kwargs: self.__read_until_impl(text, timeout, encoding, **kwargs),
        )
        self.__commands.put(item)

    def read_until_min_bytes(self, bytes_count, encoding="ascii", line_ending=b"\n"):
        item = (
            "read_until_min_bytes",
            lambda **kwargs: self.__read_lines_count_impl(bytes_count, encoding, line_ending, **kwargs),
        )
        self.__commands.put(item)

    def get_results(self):
        return self.__reads_outputs

    def history(self):
        return self.__command_history

    def __read_lines_impl(self, encoding, line_ending, **kwargs):
        telnet = kwargs["telnet"]
        size = 0
        lines = []
        while True:
            l = telnet.read_until(line_ending, 1)
            if l == b"":
                break
            clean = l.decode(encoding).rstrip()
            size += sys.getsizeof(clean)
            lines.append(clean)
        return lines, size

    def __read_lines_count_impl(self, max_count, encoding, line_ending, **kwargs):
        telnet = kwargs["telnet"]
        size = 0
        lines = []
        while size < max_count:
            l = telnet.read_until(line_ending, 1)
            clean = l.decode(encoding).rstrip()
            size += sys.getsizeof(clean)
            lines.append(clean)
        return lines, size

    def __command_impl(self, command, **kwargs):
        telnet = kwargs["telnet"]
        comm = bytes(command + "\r\n", encoding="ascii")
        telnet.write(comm)

    def __read_until_impl(self, text, timeout, encoding, **kwargs):
        telnet = kwargs["telnet"]
        out = telnet.read_until(bytes(text, encoding=encoding), timeout)
        out = out.decode(encoding)
        return out, sys.getsizeof(out)

    def reset(self):
        self.__log_print('reset() called! -> INTERNAL STATE OF TelnetCommandExecutor has been DELETED!')
        self.__reads_outputs.clear()
        self.__command_history.clear()
        self.__commands.queue.clear()
        self.__current_command = "init"

    def __set_max_window_size(self, tsocket, command, option):
        # See https://stackoverflow.com/questions/38288887/python-telnetlib-read-until-returns-cut-off-string
        if option == NAWS:
            width = struct.pack('H', 65000)
            height = struct.pack('H', 5000)
            tsocket.send(IAC + WILL + NAWS)
            tsocket.send(IAC + SB + NAWS + width + height + IAC + SE)
        elif command in (DO, DONT):
            tsocket.send(IAC + WONT + option)
        elif command in (WILL, WONT):
            tsocket.send(IAC + DONT + option)

    def get_last_command(self):
        return self.__current_command

    def run(self, debug=False):
        if debug:
            self.__log_print("=== Starting telnet session to {}:{} with a timeout of {}s === ".format(self.__target_host, self.__target_port, self.__conn_timeout))
        with telnetlib.Telnet(self.__target_host, self.__target_port, self.__conn_timeout) as tn_client:
            tn_client.set_option_negotiation_callback(self.__set_max_window_size)
            plan_size = self.__commands.qsize()
            current = 0
            while not self.__commands.empty():
                current += 1
                cmd = self.__commands.get()
                if debug:
                    self.__log_print("[{:05.2f}%] Executing command {} -> {}".format(100 * current / plan_size, cmd[0], cmd[1]))
                if "read" in cmd[0]:
                    if not self.__current_command in self.__reads_outputs:
                        self.__reads_outputs[self.__current_command] = []
                    output, size = cmd[1](telnet=tn_client)
                    if debug:
                        self.__log_print("Adding output of size {} bytes to command {}".format(size, self.__current_command))
                    self.__reads_outputs[self.__current_command].append(output)
                    if size == 0:
                        raise ValueError('No response from last command. Size = 0!')
                elif "sleep" == cmd[0]:
                    cmd[1](telnet=tn_client)
                else:
                    self.__current_command = cmd[0]
                    cmd[1](telnet=tn_client)
        if debug:
            self.__log_print("=== End of telnet session to {}:{} === ".format(self.__target_host, self.__target_port))
