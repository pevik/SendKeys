SendKeys
========

## Description

SendKeys is a utility for sending keyboard input from a terminal to a USB attached Android device.  It communicates via adb and is written in python.

## Requirements
* adb available and pathed in
* android device connected and available
* python3 (>= 3.3), python2 (>= 2.7) is still supported.

## Usage

	python3 SendKeys.py

## Notes

This utility may be slow with multiple special keys as they are sent through adb and processed one at.  Normal keys may be queued up and and sent in batches.
It is generally faster to navigate with the touchpad on Glass and use SendKeys for other data entry.

## Testing

* Tested with Python 2.7, 3.3, 3.4, 3.5 and 3.6.
* Tested with stock Google Glass, SGH-i747 with 4.1 and CM 10.2.
* Tested on Debian Sid, Ubuntu 12.04. Windows and OSX compatibility unknown.
