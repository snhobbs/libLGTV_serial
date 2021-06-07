# -*- coding: utf-8 -*-

import serial
import os
import time
import tempfile 
from filelock import FileLock
# from pprint import pprint


actual_codes = {}
common_codes = {}
actual_codes['LW_etc'] = {}
actual_codes['LW_etc'].update({
    'inputav1'              : "xb 0 20",
    'inputav2'              : "xb 0 21",
    'inputhdmi1'            : "xb 0 70",
    'inputhdmi2'            : "xb 0 71",
    'inputhdmi3'            : "xb 0 72",
    'inputhdmi4'            : "xb 0 73",
    'inputrgbpc'            : "xb 0 60",
    '3Dstatus'              : "xt 0 FF FF FF FF",
    '3Dnone'                : "xt 0 1 0 0 0",
    '3Dsbs'                 : "xt 0 0 1 0 0",
    '3Dou'                  : "xt 0 0 0 0 0"
})
reverse_code_map = {
    'LW_etc': ('LW650', 'LW650s', 'LW650S')
}
all_codes = {}
# populate model suffix lookup hash
for suffix_codes, suffixes in reverse_code_map.items():
    for suffix in suffixes:
        all_codes[suffix] = actual_codes[suffix_codes]


class LGTV:    
    def __init__(self, model, port):
        self.model = model.upper()

        # Ignore digits which indicate the TV's screen size
        if model.startswith('M'):
            self.codes = all_codes[self.model[3:]]  # Ignore the leading 'M' too
        else:
            self.codes = all_codes[self.model[2:]]

        self.port = port
        self.connection = None
        self.toggles = {
            'togglepower': ('poweron', 'poweroff'),
            'togglemute': ('mute', 'unmute'),
        }
        self.debounces = {}

    #this next line sets up the serial port to allow for communication
    #and opens the serial port you may need to change
    #ttyS0 to S1, S2, ect. The rest shouldn't need to change.
    def get_port(self):
        return serial.Serial(self.port, 9600, 8, serial.PARITY_NONE,
                serial.STOPBITS_ONE, xonxoff=0, rtscts=0, timeout=1)

    def get_port_ensured(self):
        ser = None
        while ser == None:
            try:
                ser = self.get_port()
            except serial.serialutil.SerialException:
                time.sleep(0.07)
        return ser

    def status_code(self, code):
        return code[:-2] + 'ff'

    def lookup(self, command):
        if command.startswith('toggle'):
            states = self.toggles.get(command)
            state_codes = (self.codes[states[0]], self.codes[states[1]])
            return self.toggle(self.status_code(state_codes[0]), state_codes)
        elif command.endswith('up'):
            key = command[:-2] + 'level'
            return self.increment(self.status_code(self.codes[key]))
        elif command.endswith('down'):
            key = command[:-4] + 'level'
            return self.decrement(self.status_code(self.codes[key]))
        else:
            return self.codes[command]

    # Returns None on error, full response otherwise
    def query_full(self, code):
        self.connection.write(code + '\r')
        response = self.connection.read(10)
        if self.is_success(response):
            return response

    def query_data(self, code):
        response = self.query_full(code)
        return response and response[-3:-1]

    # returns None on error, 2-char status for status commands, and True otherwise
    def query(self, command):
        if self.is_status(command):
            return self.query_data(self.lookup(command))
        else:
            return self.query_full(self.lookup(command)) and True

    def is_status(self, command):
        return command.endswith('status') or command.endswith('level')

    def is_success(self, response):
        return response[-5:-3] == 'OK'

    def hex_bytes_delta(self, hex_bytes, delta):
        return bytearray(hex(int(hex_bytes, 16) + delta)[2:4], 'ascii')

    def delta(self, code, delta):
        level = self.query_data(code)
        return code[0:6] + self.hex_bytes_delta(level, delta)

    def increment(self, code):
        return self.delta(code, +1)

    def decrement(self, code):
        return self.delta(code, -1)

    def toggle(self, code, togglecommands):
        level = self.query_data(code)
        toggledata = (togglecommands[0][-2:], togglecommands[1][-2:])
        data = toggledata[0]
        if level == toggledata[0]:
            data = toggledata[1]
        return code[0:6] + data

# ======= These are the methods you'll most probably want to use ==========

    def send(self, command):
        if command in self.debounces:
            wait_secs = self.debounces[command]
            if self.connection == None:
                self.connection = self.get_port()
            lock_path = os.path.join(tempfile.gettempdir(), '.' + command + '_lock')
            with FileLock(lock_path, timeout=0) as lock:
                response = self.query(command)
                time.sleep(wait_secs)
        else:
            if self.connection == None:
                self.connection = self.get_port_ensured()
            response = self.query(command)
        self.connection.close()
        return response

    def available_commands(self):
        print("Some features (such as a 4th HDMI port) might not be available for your TV model")
        commands = self.codes.copy()
        commands.update(self.toggles)
        for command in commands.keys():
            code = commands[command]
            if command.endswith('level'):
                print("%s : %s" % (command[:-5] + 'up', code[:-2] + '??'))
                print("%s : %s" % (command[:-5] + 'down', code[:-2] + '??'))
            else:
                print("{0} : {1}".format(command, code))

    def add_toggle(self, command, state0, state1):
        self.toggles['toggle' + command] = (state0, state1)

    def debounce(self, command, wait_secs=0.5):
        self.debounces[command] = wait_secs

# end class LGTV
