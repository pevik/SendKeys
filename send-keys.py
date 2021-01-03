#!/usr/bin/env python3
'''
This sends keys from a terminal to an android device.

Copyright (c) Casten Riepling, 2013
Copyright (c) Petr Vorel, 2014-2020
'''

SOURCE = 'github.com/pevik/SendKeys'

import curses
import shlex
import sys
import subprocess
import threading
from threading import Thread, Lock, Event
import time

if sys.version < '3':
    import urllib
    urlopen = urllib.urlopen
else:
    import urllib.request, urllib.error, urllib.parse
    urlopen = urllib.request.urlopen

versionSendKeys = '0.1'

class AdbUtils:
    adb = 'adb'
    adbArgs = []

    @staticmethod
    def adbCommand(command):
        args = [ AdbUtils.adb ] + AdbUtils.adbArgs + [ command ]
        process = subprocess.Popen(args, stdout=subprocess.PIPE)
        out, _ = process.communicate()
        return out

    @staticmethod
    def adbSendKeys(keys):
        out = None
        inputs = ''
        for x in keys:
            try:
                key = chr(x)
                if key in ('\\', "'", '"'):
                    key = '\\' + key
                inputs += key
            except ValueError:
                pass
        if inputs:
            command = 'shell input text ' + inputs
            args = [ AdbUtils.adb ] + AdbUtils.adbArgs + shlex.split(command)
            process = subprocess.Popen(args, stdout=subprocess.PIPE)
            out, _ = process.communicate()
        return out

    @staticmethod
    def adbSendSpecials(specials):
        strSpecials = ''
        for x in specials:
            strSpecials += 'input keyevent ' +str(x)+';'

        command = 'shell ' + strSpecials
        args = [ AdbUtils.adb ] + AdbUtils.adbArgs + shlex.split(command)
        process = subprocess.Popen(args, stdout=subprocess.PIPE)
        out, _ = process.communicate()
        return out

def isNewVersion():
    try:
        response = urlopen('https://raw.' + SOURCE + '/master/version')
        version = response.read().strip().decode('utf-8')

        if (version != versionSendKeys):
            return True
    except:
        pass
    return False

def checkDevice():
    resp = AdbUtils.adbCommand('devices').decode('utf-8')
    if 'device\n' not in resp:
        return False
    return True

def initCurses(scr):
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    scr.keypad(1)
    scr.nodelay(True)

def cleanupCurses(scr):
    curses.echo()
    curses.nocbreak()
    curses.curs_set(1)
    scr.keypad(0)
    scr.nodelay(False)
    curses.endwin()

def enum(**enums):
    return type('Enum', (), enums)

androidKeys = enum(
    KEYCODE_HOME = 3,
    KEYCODE_BACK = 4,
    KEYCODE_DPAD_UP = 19,
    KEYCODE_DPAD_DOWN = 20,
    KEYCODE_DPAD_LEFT = 21,
    KEYCODE_DPAD_RIGHT = 22,
    KEYCODE_CAMERA = 27,
    KEYCODE_TAB = 61,
    KEYCODE_ENTER = 66,
    KEYCODE_DEL = 67,
    KEYCODE_ESCAPE = 111,
    KEYCODE_SPACE = 62,
    KEYCODE_NUMPAD_LEFT_PAREN = 162,
    KEYCODE_NUMPAD_RIGHT_PAREN = 163,
)

unmappedCursesKeys = enum(
    KEY_BACK = 27,
    KEY_TAB = 9,
    KEY_ENTER = 10,
    KEY_SPACE = 32,
    KEY_LEFT_BRACKET = 40,
    KEY_RIGHT_BRACKET = 41,
)

cursesAndroidMap = {
                    curses.KEY_HOME:androidKeys.KEYCODE_HOME,
                    unmappedCursesKeys.KEY_BACK:androidKeys.KEYCODE_BACK,
                    curses.KEY_UP:androidKeys.KEYCODE_DPAD_UP,
                    curses.KEY_DOWN:androidKeys.KEYCODE_DPAD_DOWN,
                    curses.KEY_LEFT:androidKeys.KEYCODE_DPAD_LEFT,
                    curses.KEY_RIGHT:androidKeys.KEYCODE_DPAD_RIGHT,
                    curses.KEY_IC:androidKeys.KEYCODE_CAMERA,
                    unmappedCursesKeys.KEY_TAB:androidKeys.KEYCODE_TAB,
                    unmappedCursesKeys.KEY_ENTER:androidKeys.KEYCODE_ENTER,
                    unmappedCursesKeys.KEY_SPACE:androidKeys.KEYCODE_SPACE,
                    curses.KEY_BACKSPACE:androidKeys.KEYCODE_DEL,
                    unmappedCursesKeys.KEY_LEFT_BRACKET:androidKeys.KEYCODE_NUMPAD_LEFT_PAREN,
                    unmappedCursesKeys.KEY_RIGHT_BRACKET:androidKeys.KEYCODE_NUMPAD_RIGHT_PAREN,
}

def cursesToAndroid(c):
    if c in cursesAndroidMap:
        return True, cursesAndroidMap[c]
    else:
        return False, c

def printLegend():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK);
            stdscr.addstr(0, 0, 'SendKeys for Android')
            stdscr.addstr(0, 21, 'by Casten Riepling (2013), modified by Petr Vorel (2014-2020)')
            stdscr.addstr(3, 0, '        Special Keys        ', curses.A_UNDERLINE)
            stdscr.addstr(4, 0, 'HOME key      - Android Home')
            stdscr.addstr(5, 0, 'ESCape key    - Android Back')
            stdscr.addstr(6, 0, 'INSert key    - Take Picture')
            stdscr.addstr(7, 0, 'Arrow keys    - DPAD Keys')
            stdscr.addstr(8, 0, 'Ctrl-c        - Quit')
            if (isNewVersion()):
                stdscr.addstr(9, 0, 'Note:  new version is available at https://' + SOURCE, curses.A_REVERSE)
                stdscr.refresh()


#This handles the queue of keys in a (hopefully!) thread safe manner
class keyQueue():
    queue = []
    lock = Lock()

    #This gets a block of values that are all of the same type (special or normal).
    #We do this because we send blocks of keys of the same type since we use slightly
    #different methods for sending them over.
    def getValsBlock(self):
        self.lock.acquire()
        isSpecial, val = self._dequeue()
        vals = [val]
        while(self._size()):
            if self._peek(0)[0] == isSpecial:
                item = self._dequeue()
                vals.append(item[1])
            else:
                break
        self.lock.release()
        return isSpecial, vals

    def enqueue(self, key):
        self.lock.acquire()
        self.queue.append(key)
        self.lock.release()

    def _dequeue(self):
        item = self.queue[0]
        del self.queue[0]
        return item

    def dequeue(self):
        self.lock.acquire()
        item = self._dequeue()
        self.lock.release()
        return item

    def _size(self):
        length = len(self.queue)
        return length

    def size(self):
        self.lock.acquire()
        length = self._size()
        self.lock.release()
        return length

    def _peek(self, index):
        item = self.queue[index]
        return item

#Threadproc for reading keys asynchronously from cursers and putting them in the
#queue to send
def keyReader(scr, kq, killme):
    while(not killme.isSet()):
        key = scr.getch(1, 0)
        if (key != -1):
            isSpecial, key = cursesToAndroid(key)
            kq.enqueue([isSpecial, key])
        else:
            time.sleep(0.1)

def processKeys():
    thread = None
    killEvent = Event()
    lastFlush = time.time()
    kq = keyQueue()
    thread = Thread(target=keyReader, args=(stdscr, kq, killEvent))
    thread.name = 'keyboard-reader'
    thread.start()
    while(True):
        try:
            while (kq.size() ==  0):
                time.sleep(0.1)
            now = time.time()
            #queue up keys for 1 second before sending off since there
            #is a lot of latency sending events across adb
            if ((now - lastFlush) > 1):
                while(kq.size() > 0):
                    #get the next block of keys of the same type (special or not)
                    isSpecial, vals = kq.getValsBlock()
                    if (isSpecial):
                        AdbUtils.adbSendSpecials(vals)
                    else:
                        AdbUtils.adbSendKeys(vals)
                stdscr.refresh()
                lastFlush = time.time()
        except KeyboardInterrupt:
            break
    killEvent.set()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        AdbUtils.adbArgs = sys.argv[1:]

    if not checkDevice():
        print('no device attached')
        exit()

    stdscr = curses.initscr()
    initCurses(stdscr)
    printLegend()
    processKeys()
    cleanupCurses(stdscr)

# vim: set ft=python ts=4 sts=4 sw=4 ai expandtab :
