1. INTRODUCTION
This module is a wrapper class for all devices which can import a trigger from
eg the MR scanner to PsychoPy.
It aims to implement a uniform interface accross devices.
Currently supported devices are
    * Serial port (pyserial module)
    * Parallel port (psychopy.parallel module)
    * Cedrus device (pyxid)
    * Keyboard (psychopy.event module)
    * LaunchScan (psychopy.hardware.emulator and psychopy.event modules)
    * Dummy (emulates keyboard event every n seconds with millisecond accuracy)
Other devices may be added in the future.

PsychoPy is an open-source package for running experiments in Python.
PsychoPy was initially created and maintained by Jon Peirce.
More information on PsychoPy can be found at http://www.psychopy.org

References to PsychoPy:
Peirce, JW (2007) PsychoPy - Psychophysics software in Python. 
J Neurosci Methods, 162(1-2):8-13

Peirce JW (2009) Generating stimuli for neuroscience using PsychoPy.
Front. Neuroinform. 2:10. doi:10.3389/neuro.11.010.2008

2. CLASSES

2.0 Introduction
    This module uses the factory design pattern which means that depending on
    the input parameters, a device-specific object is returned.
    Independent of the chosen device, the interface is uniform.

    This module also support class registration. When adding a new device,
    inherit from the DeviceTrigger class and create a unique PORTTYPE class
    attribute. The new device will be added automatically to a registry which
    is accessible by the factory class.

2.1 SCANNERTRIGGER

    The ScannerTrigger class is the factory class for the requested device.
    It accepts device-specific settings and other arguments and returns a fully
    functional trigger device object.

    The ScannerTrigger class implements only one public method:

    class ScannerTrigger.create(win, portType=None, portConfig=None,
                    timeout=999, globalClock=None, esc_key='escape')

        win: psychopy.visual.Window object
            The Window object in which the experiment runs

        portType: 'DUMMY', 'KEYBOARD', 'SERIAL', 'PARALLEL', 'LAUNCHSCAN'
            Type of port for triggering

        portConfig: None or dictionary (default: None)
            Dictionary with port-specific settings (see below)

        timeout: int (default: 999)
            Timeout value (in seconds) to abort waiting the start of a scan

        globalClock: None or psychopy.core.Clock object (default: None)
            The trigger device object needs a clock to report times. If a
            global clock is provided, it will reset with the first trigger
            received.
            If none is provided, an internal clock will be instantiated.
            Notice: if the globalClock is reset after the first scanner
            trigger, the reported times will be relative to the last reset.

        logLevel: one of the possible levels defined by the psychopy.logging
            module (default: logging.DATA) or a custom log level.
            All events will be logged at the defined log level.

        esc_key: string (default: 'escape')
            Keyboard character to manually abort waiting the first trigger.

        device: device-specific object
            If an instantiated device object is provided, all device-specific
            settings in portConfig (see below) will be disregarded and the
            provided device object will be used for the triggering.
            This allows to share eg a serial port object between the
            scannertrigger and other functions/classes.

    Possible inputs for portType and portConfig

    * DUMMY
        A DUMMY object emits a trigger every n seconds with millisecond
        accuracy.

        tr: float (default: 1.0)
            Simulated TR in seconds

        example
            portType = 'DUMMY'
            MR_settings_dummy = {
                'tr': 1.0,
            }

    * SERIAL
        A SERIAL object wraps a pyserial object.
        The input parameters for the serial port trigger are compatible with
        the parameters for the pyserial module:

        port: none or device name
        baudrate: int (default: 9600)
            Baud rate such as 9600 or 115200 etc.
        bytesize: FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS (default: EIGHTBITS)
            Number of data bits.
        parity: PARITY_NONE, PARITY_EVEN, PARITY_ODD PARITY_MARK, PARITY_SPACE
                (default: PARITY_NONE)
            Enable parity checking.
        stopbits: STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO
                  (default: STOPBITS_ONE)
            Number of stop bits.
        timeout: None or float (default: None)
            Set a read timeout value.
        xonxoff: bool (default: False)
            Enable software flow control.
        rtscts: bool (default: False)
            Enable hardware (RTS/CTS) flow control.
        dsrdtr: bool (default: False)
            Enable hardware (DSR/DTR) flow control.
        write_timeout: float (default: None)
            Set a write timeout value.
        inter_byte_timeout: float (default: None)
            Inter-character timeout, None to disable.
        exclusive: bool (default: None)
            Set exclusive access mode (POSIX only). A port cannot be opened in
            exclusive access mode if it is already open in exclusive access
            mode.

        Some additional parameters are required:

        sync: key value (default: '5')
            Key for syncing

        Remark: timeout value of pyserial is ignored to avoid blocking.

        More info: http://pyserial.readthedocs.io/en/latest/pyserial_api.html

        example
            portType = 'SERIAL'
            MR_settings_serial = {
                'port': 'COM1',
                'baudrate': 9600,
                'sync': '5'
            }

    * PARALLEL
        A PARALLEL object wraps the psychopy.parallel module.
        Notice:
            Make sure that when running on Microsoft Windows, the inpout32.dll
            file shipped with this module is installed properly.
            When running 64bit Python, you will need to install the 64bit
            version (but this has not been tested).

        address: string
            Memory address or device node of the parallel port
            ('eg 0x0378 or /dev/parport0')
        pin: int (default: 10)
            Pin number to read the value from.
        edge: int (default: 1)
            type of edge to trigger on, possible values are:
                ScannerTrigger.FALLING (-1)
                ScannerTrigger.RISING (1)
                ScannerTrigger.BOTH (0)

        example
            portType = 'parallel'
            MR_settings_parallel = {
                'address': 0x0378,
                'pin': 10
                'edge': ScannerTrigger.RISING
            }

    * CEDRUS
        A CEDRUS object wraps the pyxid module.

        devicenr: int (default: 0)
            Devicenumber of the particular XID device.

        sync: key value as integer (default: 4)
            Key for syncing. Due to keymapping in by pyxid, button 5 maps to 4
            in PsychoPy.

        example
            portType = 'cedrus'
            MR_settings_cedrus = {
                'devicenr': 0,
                'sync': 4
            }

    * KEYBOARD
        A KEYBOARD object wraps the keyboard part of the psychopy.events
        module.

        keyList: list of key values (default: '5')
            List of keys which are detected as a scan trigger
        maxWait: float (default: float('inf'))
            Maximum number of seconds to wait for a key press

        example
            portType = 'KEYBOARD'
            MR_settings_keyboard = {
                'keyList': 't',
                'maxWait': 10
            }

    * LAUNCHSCAN
        A LAUNCHSCAN object uses the psychopy.hardware.emulator.launchScan
        function to start synchronization.
        After the first detected trigger, a KEYBOARD object catches the
        triggers.

        This functionality can also be implemented in a script by using the
        launchScan function and a seperate KEYBOARD object.

        The input parameters for the launchScan trigger are compatible with the
        arameters for the launchScan function.
        Some parameters (eg win) are ignored if not necessary.

        wait_msg: string (default: 'waiting for scanner...')
            Waiting message displayed on the Window
        wait_timeout: float (default: 300)
            Time in seconds that launchScan will wait before assuming something
            went wrong and exiting. Defaults to 300sec (5 min).
            Raises a RuntimeError if no sync pulse is received in the allowable
            time.
        instr: string (default: 'select Scan or Test')
            Instructions to be displayed to the scan operator during mode
            selection.
        mode: None, 'Test' or 'Scan'
            Runs launchScan in the selected mode. If None, the operator is able
            to choose.
        esc_key: key character (default: 'escape')
            Key to be used for user-interrupt during launch.

        More info: http://www.psychopy.org/api/hardware/emulator.html

        example
            portType = 'LAUNCHSCAN'
            MR_settings_launchScan = {
                'wait_msg': 'Waiting for scanner',
                'wait_timeout'
                'esc_key': 'escape',
                'log': True,
                'mode': 'Scan',
                'settings': {
                    'TR': 1,
                    'volumes': 100,
                    'sync': 't',
                    'skip': 0,
                    'sound': False
                }
            }


2.2 DEVICETRIGGER
    This is the base class for all trigger devices. The classes should inherit
    from this class to be added to the registry.

    Class attributes:
        registry: dictionary
            List of implemented trigger devices
            (classes inheriting from DeviceTrigger)

        PORTTYPE: string
            A unique type for the device.

    Instance attributes:
        triggerCnt: int
            Counts elapsed triggers.
            This attribute has a getter, intended for internal use.
            Use this with caution because this can influence the logging!

        triggerTime: float
            Contains the time of the last trigger.

        firstTriggerTime: float
            Contains the time of the very first trigger, including any dummy
            scans.

        port: device object
            If applicable, returns the fully instantiated object
            (eg serial.Serial object, parallel.Parallel object,
            pyxid.ResponseDevice), otherwise None.

    Methods:
        Override the necessary methods.

        def open():
            Initialize the encapsulated trigger device.

            Exception:
                Raises a DeviceTriggerException if port not opened.

        def close():
            Close and cleanup.

        def getTrigger()
            Checks if a trigger has been received.

            Returns:
                True if trigger detected, False if not.

        def waitForTrigger(skip=0)
            Wait for the trigger.

            At the first detection of a trigger, the globalClock is reset.
            The time of the first trigger (TRIGGER 0) is the time since the
            last reset of the globalClock.
            Consecutive times are relative to the first trigger (TRIGGER 0)
            Be aware that a reset of the globalClock further in the code will
            be reflected in the reported timing values!
            Every detected trigger will be logged at level EXP

            Keyword args:
                skip: number of triggers to skip (default: 0)
                    The skipped triggers will be logged, but the function will
                    not return before the requested number of triggers are
                    skipped.

            Returns:
                True if trigger (after skipped triggers) is detected, False if
                none detected or interrupted or timed out.

            Exception:
                Raises a DeviceTriggerTimeoutException when the timeout is
                exceeded.
                Raises a DeviceTriggerException when user-interrupted.

    The DeviceTrigger class also implements a getTrigger function which blocks
    further execution. Overriding in the child classes is not necessary.
        def getTriggerBlock():
            Checks if a trigger has been received.

            This function is blocking further execution and returns when
                - a trigger is received
                - the escape key has been pressed
                - the function has timed out

            Returns:
                True if trigger detected, False if none detected or interrupted
                or timed out.

            Exception:
                Raises a DeviceTriggerException when user-interrupted.

2.3 Device-specific classes
    Following classes have been implemented:
        SerialPortTrigger
        ParallelPortTrigger
        DummyTrigger
        KeyboardTrigger
        LaunchScanTrigger
        CedrusTrigger

    The user can instantiate on object from one of these classes directly.

    The initialization method is the same for all classes:
    def __init__(self, win, globalClock, portConfig=None, **kwargs):
        Args:
            win: psychopy.visual.Window object
            globalClock: global clock object (required)

        Keyword args:
            portConfig: dictionary with device-specific settings (as described
            above)
            timeout: timeout value (in seconds) to abort waiting the start
                of a scan
            esc_key: keyboard key value to abort waiting the start of
                a scan manually
            device: fully configured device object.
                If provided, all device-specific settings in portConfigKeyList

        Exception:
            Raises a portNotFoundError (DeviceTriggerException) when no port
            is defined (a port name or a compatible device instance).
    Other functions are described in 2.2

2.5 Exceptions
    class DeviceTriggerTimeoutException
        Raised when a timeout occurs.

    class DeviceTriggerException
        Raised in case of general exceptions.

    The module has some DeviceTriggerException instances with a specific
    message.
    Those instances are raised where appropriate.


3. LOGGING

The DeviceTrigger class logs all events by default at level logging.DATA.
This can be changed during the creation of the trigger.
The output generated in the log is:
<logging time> TRIGGER <triggerCnt> <triggerTime>.
The times reported by the logging module are less accurate (a variability of
around 2ms is not unusual on moderate hardware). The DeviceTrigger.triggerTime
value (in the log or using the instance attribute) attribute contains the most
accurate time.
In case of a keyboard trigger, the time reported by the device trigger is the
ame as the time reported by the logging module for the keypress event of the
trigger at logging level logging.DATA.
Make sure to execute logging.flush() to write the logs to the output streams
but don't exaggerate as flushing consumes a lot of time!
It is up to the user to implement logging of the triggers if the logging module
is not being used.

Note: When using the waitForTrigger method, the triggers below the skip value
are logged by the logging module. However, the triggerTime value will only
contain the time of the trigger exiting the waitForTrigger method.
If this data is needed, one should implement a custom waitForTrigger method
using the getTrigger method and the triggerCnt and triggerTime attributes.

A possible implementation can be:
    def waitForTrigger(triggerDevice, globalClock, timeout=0, skip=0):
        logging.exp('Wait for trigger ...')
        skipVal = skip
        timeOutClock = core.Clock()
        timeOutClock.reset()
        while not event.getKeys(keyList=self.extraArgs['esc_key']):
            if triggerDevice.getTrigger():
                print('TRIGGER\t{0:d}\t{1:f}'.format(triggerDevice.triggerCnt,
                                                    triggerDevice.triggerTime))
                logging.flush()
                if skipVal == 0:
                    return True
                else:
                    skipVal -= 1
                if self.timeOutClock.getTime() > self.extraArgs['timeout']:
                    raise waitTimeoutError
        raise abortError
        return False

4. KNOWN ISSUES
There is an issue with the pyo library imported in PsychoPy.
When importing the sound module from PsychoPy, the core.quit() function might
not exit properly. This can be resolved by importing the sound module as first
in the import statements of your script.

PsychoPy crashes when virtual COM ports are being used. The crash happens in
the device detection loop in pyxid.

5 INSTALLATION
Copy the appropriate folder to the root directory of your main script which
imports the ScannerTriger Module. 
Make sure the folder is called scannertrigger.

6. USAGE

An example script demo.py using the ScannerTrigger module is shipped with this
module.

Documentation of demo.py:

Demo of the ScannerTrigger module.

Idea
====
This script, written in Python using PsychoPy demonstrates the use of the
ScannerTrigger module.

Input
=====
    Triggering - device to receive triggers from
    Scans to skip - number of triggers to skip before continuing

To adjust device specific parameters, edit the appropriate MR_settings
dictionary below.

Output
======
The script will detect triggers received from the selected device and displays
some data:
    Trigger number - number of received trigger (zero based, it's Python!)
                     if scans to skip is greater than 0, the first shown
                     trigger is trigger <scans to skip>
    Onset time - time elapsed since the first triggered
    Delta time - time between last and one-but-last triggered
    Skip scans - number of scans to skip
The script will loop until the escape key has been pressed or after 100s have
elapsed (can be adjusted).

After finishing the loop, a histogram is displayed from the delta times.
The script also prints out the mean, standard deviation, maximum and minimum of
the delta times.

Remark
======
This script was developed in PsychoPy 1.90.2 and runs in the Python2 and
Python3 version.

Copyright (C) 2018 Pieter Vandemaele
Distributed under the terms of the GNU General Public License (GPL).

7. PEP8 COMPLIANCY
All files are PEP8 compliant (apart from one or two E5012 and W503 codes).
For W503, breaking before or after the binary operator is allowed as long as
the convention is consistent locally.
See https://www.python.org/dev/peps/pep-0008/ for more information.