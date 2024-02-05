"""Classes implementing a uniform interface to possible MRI scanner triggers.

This module is a wrapper class for all devices which can import a trigger from
eg the MR scanner to PsychoPy.
It aims to implement a uniform interface accross devices.
Currently supported devices are
    * Serial port (pyserial module)
    * Parallel port (psychopy.parallel module)
    * Cedrus device (pyxid)
    * Keyboard (psychopy.event module)
    * LaunchScan (psychopy.hardware.emulator and psychopy.event modules)
    * Dummy (emulates a keyboard event every n seconds with millisecond
      accuracy)
Other devices may be added in the future.

For detailed information and an example, see the README.TXT file shipped with
this module.

Copyright (C) 2018 Pieter Vandemaele
Distributed under the terms of the GNU General Public License (GPL).
"""

# Import statements
import pyxid2 as pyxid
import serial
from abc import ABCMeta, abstractmethod
from psychopy import visual, core, logging, event, parallel
from psychopy.hardware.emulator import launchScan


# Defining edges
RISING = 1
FALLING = -1
BOTH = 0


class DeviceTriggerException(IOError):
    """Base class for devicetrigger related exceptions."""


class DeviceTriggerTimeoutException(DeviceTriggerException):
    """Write timeouts give an exception"""

waitTimeoutError = DeviceTriggerTimeoutException('Waiting for trigger timeout')
portNotOpenError = DeviceTriggerException('Attempting to use a port that is not open')
portNotFoundError = DeviceTriggerException('Port not found')
abortError = DeviceTriggerException('Experiment aborted by the user')


def __process_kwargs__(kwargs, keyList):
    """Extract key-value pairs from a dict using a list of requested keys."""
    if kwargs is None or keyList is None:
        return None
    else:
        return {key: kwargs[key] for key in keyList if key in kwargs}


class DeviceTriggerMeta(type):
    """Metaclass for DeviceTrigger types, used to register devices."""

    # We use __init__ rather than __new__ here because we want
    # to modify attributes of the class *after* they have been
    # created.

    def __init__(cls, name, bases, dct):
        if cls.portType() is None:
            # this is the base class.  Create an empty registry
            cls.registry = {}
        else:
            # this is a derived class.  Add cls to the registry
            device_id = interface_id = cls.portType().lower()
            cls.registry[device_id] = cls

        super(DeviceTriggerMeta, cls).__init__(name, bases, dct)


class DeviceTrigger(metaclass=DeviceTriggerMeta):

    """Abstract base class for trigger devices.

    All implemented trigger devices should inherit from this base class.
    """
    _PORTTYPE = None

    @classmethod
    def portType(cls):
        """Return the type of the port."""
        if cls._PORTTYPE is None:
            return None
        else:
            return cls._PORTTYPE.lower()

    @abstractmethod
    def __init__(self, globalClock, portConfig=None,
                 portConfigKeyList=None, extraConfigKeyList=None,
                 logLevel=logging.DATA, device=None, **kwargs):
        """Abstract bace class constructor for DeviceTrigger class.

        Args:
            globalClock: global clock object (required)

        Keyword args:
            portConfig: dictionary with all settings to setup the port,
                provided by the user (default: None)
            portConfigKeyList: dictionary ('library') with specific parameters
                to initialize the selected port (default: None)
            extraConfigKeyList: dictionary ('library') with extra settings
                (eg sync value) (default: None)
                both configKeyLists are used to split the portConfig dictionary
                in port arguments and extra arguments
                (eg timeout and escape key)
            timeout: timeout value (in seconds) to abort waiting the start
                of a scan (default: 999)
            esc_key: keyboard key value to abort waiting the start of
                a scan manually (default: 'escape')
            logLevel: one of the possible levels defined by the
                psychopy.logging module (default: logging.DATA)
                All events will be logged at the defined log level.

            device: fully configured device object (eg pyserial object).
                If provided, all device-specific settings in portConfigKeyList
                will be ignored.

        Returns:
            Nothing
        """

        # Split port configuration in port arguments and extra arguments
        self._portArgs = __process_kwargs__(portConfig, portConfigKeyList)
        self.extraArgs = __process_kwargs__(portConfig, extraConfigKeyList)

        # Reset trigger counter
        self.triggerCnt = -1

        # Set global clock
        self.globalClock = globalClock

        # Set clock for timeout of synchronization
        # - last trigger onset
        # - some internal use clocks
        self.timeOutClock = core.Clock()

        # Some internal used times
        # First scan time
        self._firstTriggerTime = 0
        # Last scan time
        self._lastTriggerTime = globalClock.getTime()
        # Internally used times
        self._dtime = self._lastTriggerTime
        self._incTime = self._lastTriggerTime

        # Set timeout value
        if 'timeout' not in kwargs:
            self.extraArgs.update({'timeout': 999})
        else:
            self.extraArgs.update({'timeout': kwargs['timeout']})

        # Set escape key
        if 'esc_key' not in kwargs:
            self.extraArgs.update({'esc_key': 'escape'})
        else:
            self.extraArgs.update({'esc_key': kwargs['esc_key']})

        # Set log level
        self.logLevel = logLevel

        # Set device
        if 'device' != None:
            self.extraArgs.update({'device': device})

        # Set port
        self._port = None

    def _str__(self):
        """String representation of class."""
        return str(cls.portType + ": " + str(self._portArgs))

    @abstractmethod
    def open(self):
        """Initializes the triggerdevice. (Abstract Method)

        Args:
            None

        Returns:
            True if trigger successfull, False if none unsuccessfull

        Exception:
            Raises a DeviceTriggerException if port could not be opened.
        """
        logging.log('Initialized trigger ' + self.portType(), self.logLevel)

    @abstractmethod
    def close(self):
        """Closes the triggerdevice. (Abstract Method)

        Args:
            None

        Returns:
            Nothing
        """
        logging.log('Closed trigger ' + self.portType(), self.logLevel)

    @property
    def triggerCnt(self):
        """Returns trigger counter."""
        return self._triggerCnt

    @triggerCnt.setter
    def triggerCnt(self, value):
        """Set trigger counter.

        Use this carefully as it can mess up you log files!
        """
        self._triggerCnt = value

    @property
    def triggerTime(self):
        """Returns last trigger time."""
        return self._lastTriggerTime

    @property
    def firstTriggerTime(self):
        """Returns time of the first scan."""
        return self._firstTriggerTime

    '''
    @triggerTime.setter
    def triggerTime(self, value):
        """Set trigger time.

        Use this carefully as it can mess up you log files!
        """
        self._lastTriggerTime = value
    '''

    @property
    def port(self):
        """Returns the port object."""
        return self._port

    def getTriggerBlock(self):
        """Checks if a trigger has been received.

        This function is blocking further execution and returns when
            - a trigger is received
            - the escape key has been pressed
            - the function has timed out

        Returns:
            True if trigger detected, False if none detected or interrupted or
            timed out.

        Exception:
            Raises a DeviceTriggerException when user-interrupted.
        """
        # Reset the timeout clock
        self.timeOutClock.reset()

        while not event.getKeys(keyList=self.extraArgs['esc_key']):
            if self.getTrigger():
                return True
            if self.timeOutClock.getTime() > self.extraArgs['timeout']:
                raise waitTimeoutError
        raise abortError
        return False

    @abstractmethod
    def getTrigger(self):
        """Checks if a trigger has been received.  (Abstract Method)

        This function is non-blocking and returns immediately after execution.

        Returns:
            True if trigger detected, False if none detected.
        """
        return False

    @abstractmethod
    def waitForTrigger(self, skip=0):
        """Wait for the trigger.

        At the first detection of a trigger, the globalClock is reset.
        The time of the first trigger (TRIGGER 0) is the time since the last
        reset of the globalClock.
        Consecutive times are relative to the first trigger (TRIGGER 0).

        Be aware that a reset of the globalClock further in the code will be
        reflected in the reported timing values!
        Every detected trigger will be logged at the level provided or by
        default at loglevel DATA.

        Keyword args:
            skip: number of triggers to skip (default: 0)

        Returns:
            True if trigger (after skipped triggers) is detected, False if none
            detected or interrupted or timed out.

        Exception:
            Raises a DeviceTriggerTimeoutException when the timeout is exceeded.
            Raises a DeviceTriggerException when user-interrupted.
        """
        logging.log('Wait for trigger ...', self.logLevel)
        logging.flush()
        skipVal = skip
        self.timeOutClock.reset()
        self._incTime = self.globalClock.getTime()
        triggered = False
        while not event.getKeys(keyList=self.extraArgs['esc_key']):
            if self.getTrigger():
                if skipVal == skip:
                    self._firstTriggerTime = self.triggerTime
                    triggered = True
                if skipVal <= 0:
                    return True
                skipVal -= 1
            if ((self.timeOutClock.getTime() > self.extraArgs['timeout'])
                    and not triggered):
                raise waitTimeoutError
        raise abortError
        return False

    def _logTrigger(self, trigTime=None):
        """Do some housekeeping when a trigger is detected.

        Write to the logs, increment the counter and keep track of time.

        Returns:
            True if trigger detected.
        """
        if self._trigger:
            # Trigger detected
            self.triggerCnt += 1
            self._lastTriggerTime = self._dtime
            logging.log('TRIGGER\t{0:d}\t{1:f}'.format(self.triggerCnt,
                        self.triggerTime), self.logLevel)
        return self._trigger


####################################################################
# DUMMY                                                            #
####################################################################

class DummyTrigger(DeviceTrigger):
    """Dummy trigger.

    Simple trigger which emulates a keyboard press every n seconds with
    submillisecond accuracy.
    """

    _PORTTYPE = 'DUMMY'

    def __init__(self, win, globalClock, portConfig=None, **kwargs):
        """Constructor of DummyTrigger.

        Args:
            win: psychopy.visual.Window object
            globalClock: global clock object (required)

        Keyword args:
            portConfig: dictionary with keys
                tr: port argument - simulated TR in seconds (default: 1)
            timeout: timeout value (in seconds) to abort waiting the start
                of a scan
            esc_key: keyboard key value to abort waiting the start of
                a scan manually
            device: fully configured device object.
                If provided, all device-specific settings in portConfigKeyList
                will be ignored. (not used)
        """

        # Set key lists
        portConfigKeyList = ['tr']
        extraConfigKeyList = []

        # Base class constructor
        super(DummyTrigger, self).__init__(
                globalClock, portConfig, portConfigKeyList,
                extraConfigKeyList, **kwargs)

        # Set default values
        if 'tr' not in self._portArgs:
            self._portArgs.update({'tr': 1.0})

        logging.log('Created trigger DUMMY: ' +
                    str(self._portArgs) + str(self.extraArgs), self.logLevel)

    def getTrigger(self):
        """Checks if a trigger has been received for DummyTrigger.

        Returns:
            True if trigger detected, False if none detected.
        """
        # Avoid hogging up the CPU for the whole waiting period
        self._incTime = self._incTime + self._portArgs['tr']
        core.wait(max(self._portArgs['tr'] - 0.2, 0.0))

        # Update the timer for the next cycle
        while self.globalClock.getTime() < self._incTime:
            pass

        self._dtime = self.globalClock.getTime()

        # Trigger detected
        self._trigger = True

        return self._logTrigger()


####################################################################
# SERIAL                                                           #
####################################################################

class SerialPortTrigger(DeviceTrigger):
    """Serial port trigger.

    Wrapper for the serial port (pyserial).
    """

    _PORTTYPE = 'SERIAL'

    def __init__(self, win, globalClock, portConfig=None, **kwargs):
        """Constructor of SerialPortTrigger.

        Args:
            win: psychopy.visual.Window object
            globalClock: global clock object (required)

        Keyword args:
            portConfig: dictionary with keys
                parameters defined by pyserial: port arguments
                sync: extra argument - sync value (default: 5)
            timeout: timeout value (in seconds) to abort waiting the start
                of a scan
            esc_key: keyboard key value to abort waiting the start of
                a scan manually
            device: fully configured serial.Serial object.
                If provided, all device-specific settings in portConfigKeyList
                will be ignored.

        Exception:
            Raises a DeviceTriggerException when no port is defined
            (a port name or a serial port device).

        Remark: timeout value of pyserial is ignored to ignore blocking.

        More info: http://pyserial.readthedocs.io/en/latest/pyserial_api.html
        """
        # Configure key lists
        portConfigKeyList = ['port', 'baudrate',
                             'bytesize', 'parity', 'stopbits', 'timeout']
        extraConfigKeyList = ['sync', ]

        # Base class constructor
        super(SerialPortTrigger, self).__init__(
                globalClock, portConfig, portConfigKeyList,
                extraConfigKeyList, **kwargs)

        # Configure default values
        if 'sync' not in self.extraArgs:
            self.extraArgs.update({'sync': b'5'})

        if 'device' in self.extraArgs:
            if isinstance(self.extraArgs['device'], serial.Serial):
                self._port = self.extraArgs['device']

        if 'port' not in self._portArgs and self._port is None:
            logging.error('No serial port defined')
            raise portNotFoundError

        # Force timeout setting to 0
        self._portArgs.update({'timeout': 0})

        if type(self.extraArgs['sync']) is int:
            sync = bytes(chr(self.extraArgs['sync']), 'ascii')
        elif type(self.extraArgs['sync']) is str:
            sync = bytes(self.extraArgs['sync'], 'ascii')
        else:
            sync = self.extraArgs['sync']
        # sync = bytes(self.extraArgs['sync'], encoding='UTF-8')

        self.extraArgs.update({'sync': sync})

        if self._port is None:
            logging.log('Created trigger SERIAL: ' +
                        str(self._portArgs) + str(self.extraArgs),
                        self.logLevel)
        else:
            logging.log('Created trigger SERIAL: ' + str(self._port),
                        self.logLevel)

    def open(self):
        """Initialization of SerialPortTrigger.

        Exception:
            Raises a DeviceTriggerException if port could not be opened.
        """
        try:
            if self._port is None:
                self._port = serial.Serial(**self._portArgs)
            else:
                pass
            logging.log('Opened serial port ' + str(self._port), self.logLevel)
        except serial.SerialException as e:
            logging.error('Could not open serial port ' +
                          self._portArgs['port'])
            raise portNotOpenError

        super(SerialPortTrigger, self).open()

    def close(self):
        """Closing and cleanup of SerialPortTrigger."""
        if type(self._port) is serial.Serial:
            self._port.close()
        super(SerialPortTrigger, self).close()

    def getTrigger(self):
        """Checks if a trigger has been received for SerialPortTrigger.

        Returns:
            True if trigger detected, False if none detected.
        """
        self._trigger = bool(self._port.read(1) == self.extraArgs['sync'])
        self._dtime = self.globalClock.getTime()
        return self._logTrigger()


####################################################################
# PARALLEL                                                         #
####################################################################

class ParallelPortTrigger(DeviceTrigger):
    """Parallel port trigger.

    Wrapper for the parallel port (psychopy.parallel).
    """

    _PORTTYPE = 'PARALLEL'

    def __init__(self, win, globalClock, portConfig=None, **kwargs):
        """Constructor of ParallelPortTrigger.

        Args:
            win: psychopy.visual.Window object
            globalClock: global clock object (required)

        Keyword args:
            portConfig: dictionary with keys
                address: port arguments - address of the parallel port as
                    needed in psychopy.parallel
                pin: extra argument - pin to read the trigger from
                    (default: 10)
            timeout: timeout value (in seconds) to abort waiting the start
                of a scan
            esc_key: keyboard key value to abort waiting the start of
                a scan manually
            device: fully configured parallel.Parallel object.
                If provided, all device-specific settings in portConfigKeyList
                will be ignored.

        Exception:
            Raises a DeviceTriggerException when no address is defined
            (an address or a parallel port device).
        """
        # Configure key lists
        portConfigKeyList = ['address']
        extraConfigKeyList = ['pin', 'edge']

        # Base class constructor
        super(ParallelPortTrigger, self).__init__(
                globalClock, portConfig, portConfigKeyList,
                extraConfigKeyList, **kwargs)

        # Configure default values

        if 'pin' not in self.extraArgs:
            self.extraArgs.update({'pin': 10})

        if 'edge' not in self.extraArgs:
            self.extraArgs.update({'edge': 1})

        if 'device' in self.extraArgs:
            if isinstance(self.extraArgs['device'], parallel.ParallelPort):
                self._port = self.extraArgs['device']

        if 'address' not in self._portArgs and self._port is None:
            logging.error('No parallel port defined')
            raise portNotFoundError

        self._triggered = False
        self._state = False
        self._prevstate = False

        if self._port is None:
            logging.log('Created trigger PARALLEL: ' +
                        str(self._portArgs) + str(self.extraArgs),
                        self.logLevel)
        else:
            logging.log('Created trigger PARALLEL: ' + str(self._port),
                        self.logLevel)

    def open(self):
        """Initialization of ParallelPortTrigger.

        Exception:
            Raises a DeviceTriggerException if port could not be opened.
        """
        try:
            if self._port is None:
                self._port = parallel.ParallelPort(**self._portArgs)
            else:
                pass
            core.wait(0.5)
            logging.log('Opened parallel port ' + str(self._port),
                        self.logLevel)
        except Exception as e:
            logging.error('Could not open parallel port ' +
                          self._portArgs['address'])
            raise portNotOpenError

        super(ParallelPortTrigger, self).open()

    def getTrigger(self):
        """Checks if a trigger has been received for ParallelPortTrigger.

        Returns:
            True if trigger detected, False if none detected.
        """
        self._state = bool(self._port.readPin(self.extraArgs['pin']))

        # Check if a state change occurred
        self._trigger = (self._state != self._prevstate)

        if self._trigger:
            self._dtime = self.globalClock.getTime()
            # Check for only rising or falling edges or both
            if self._prevstate:
                # falling edge
                self._trigger = (self._trigger and self.extraArgs['edge'] <= 0)
            else:
                self._trigger = (self._trigger and self.extraArgs['edge'] >= 0)
            self._prevstate = self._state

        return self._logTrigger()


####################################################################
# KEYBOARD                                                         #
####################################################################

class KeyboardTrigger(DeviceTrigger):
    """Keyboard trigger.

    Wrapper for the keyboard (psychopy.event).

    """

    _PORTTYPE = 'KEYBOARD'

    def __init__(self, win, globalClock, portConfig=None, **kwargs):
        """Constructor of KeyboardTrigger.

        Args:
            win: psychopy.visual.Window object
            globalClock: global clock object (required)

        Keyword args:
            portConfig: dictionary with keys
                parameters as needed by psychopy.event.getKeys(): port argument
                    keyList:  list of keys which act as a trigger (default: 5)
                    maxWait: maximum number of seconds for which to wait
                        for keys (default: inf)
            timeout: timeout value (in seconds) to abort waiting the start
                of a scan
            esc_key: keyboard key value to abort waiting the start of
                a scan manually
            device: not used
        """
        # Configure key lists
        portConfigKeyList = ['maxWait', 'keyList']
        extraConfigKeyList = []

        # Base class constructor
        super(KeyboardTrigger, self).__init__(
                globalClock, portConfig, portConfigKeyList,
                extraConfigKeyList, **kwargs)

        # Configure default values
        if 'keyList' not in self._portArgs:
            self._portArgs['keyList'] = '5'

        self.extraArgs['keyList'] = self._portArgs['keyList']

        if isinstance(self._portArgs['keyList'], (list,)):
            self.extraArgs['keyList'].append(self.extraArgs['esc_key'])
        else:
            self.extraArgs['keyList'] = [
                self.extraArgs['keyList'], self.extraArgs['esc_key']]

        logging.log('Created trigger KEYBOARD: ' +
                    str(self._portArgs) + str(self.extraArgs), self.logLevel)

    def getTrigger(self):
        """Checks if a trigger has been received for KeyboardTrigger.

        Returns:
            True if trigger detected, False if none detected.
        """
        keyList = dict(event.getKeys(keyList=self._portArgs['keyList'],
                       timeStamped=self.globalClock))
        self._trigger = bool(keyList)
        self._dtime = self.globalClock.getTime()
        return self._logTrigger()


####################################################################
# LAUNCHSCAN                                                       #
####################################################################

class LaunchScanTrigger(DeviceTrigger):
    """LaunchScan trigger.

    Wrapper for the launchScan function (psychopy.hardware.emulator)

    """

    _PORTTYPE = 'LAUNCHSCAN'

    def __init__(self, win, globalClock, portConfig=None, **kwargs):
        """Constructor of LaunchScanTrigger.

        Args:
            win: psychopy.visual.Window object
            globalClock: global clock object

        Keyword args:
            portConfig: dictionary with keys
                parameters as needed by psychopy.hardware.emulator.launchScan()
                : port arguments
            timeout: timeout value (in seconds) to abort waiting the start
                of a scan
            esc_key: keyboard key value to abort waiting the start of
                a scan manually
            device: not used

        Exception:
            Raises a DeviceTriggerException when no KeyboardTrigger instance
            could be created.
        """
        self.win = win

        # Configure key lists
        portConfigKeyList = ['globalClock', 'wait_timeout',
                             'esc_key', 'mode', 'instr', 'wait_msg']
        extraConfigKeyList = ['settings']

        # Base class constructor
        super(LaunchScanTrigger, self).__init__(
                globalClock, portConfig, portConfigKeyList,
                extraConfigKeyList, **kwargs)

        if ('settings' not in self.extraArgs or
                ('TR' not in self.extraArgs['settings'] or
                    'volumes' not in self.extraArgs['settings'])):
            logging.error('No valid settings parameters defined')

        # Configure default values
        if 'sync' not in self.extraArgs['settings']:
            self.extraArgs.settings.update({'sync': '5'})

        if 'sync' not in self.extraArgs['settings']:
            self.extraArgs.settings.update({'sync': '5'})

        kb_settings = {
            'keyList': self.extraArgs['settings']['sync'],
            'maxWait': 10
        }

        # Create a keyboard trigger to handle keypresses in test mode
        try:
            self.kb = KeyboardTrigger(
                win,  portConfig=kb_settings, globalClock=globalClock,
                timeout=self.extraArgs['timeout'],
                esc_key=self.extraArgs['esc_key'])
            self.kb.open()
        except Exception as e:
            logging.error('Could not open serial port ' +
                          self._portArgs['port'])
            raise portNotFoundError
        logging.log('Created trigger LAUNCHSCAN: ' +
                    str(self._portArgs) + str(self.extraArgs), self.logLevel)

    def open(self):
        """Initialization of LaunchScanTrigger."""
        super(LaunchScanTrigger, self).open()

    def close(self):
        """Closing and cleanup of LaunchScanTrigger."""
        self.kb.close()
        super(LaunchScanTrigger, self).close()
        pass

    def waitForTrigger(self, skip=0):
        """Wait for the trigger.

        At the first detection of a trigger, the globalClock is reset.
        The time of the first trigger (TRIGGER 0) is the time since the last
        reset of the globalClock.
        Consecutive times are relative to the first trigger (TRIGGER 0).

        Be aware that a reset of the globalClock further in the code will be
        reflected in the reported timing values!
        Every detected trigger will be logged at the level provided or by
        default at loglevel DATA.

        Keyword args:
            skip: number of triggers to skip (default: 0)

        Returns:
            True if trigger (after skipped triggers) is detected, False if none
            detected or interrupted or timed out.

        Exception:
            Raises (escalates) the exception from launchScan and the
            exceptions from KeyboardTrigger __init__() and open() functions.
        """
        logging.log('Wait for trigger ...', self.logLevel)
        logging.flush()
        try:
            launchScan(self.win, self.extraArgs['settings'], **self._portArgs)
            self._trigger = True
        except Exception as e:
            logging.error('Could not initialize trigger LAUNCHSCAN')
            raise e
        self.kb.triggerCnt = 0
        self._dtime = self.globalClock.getTime()
        self._firstTriggerTime = self._dtime
        self._logTrigger()
        if skip > 0:
            try:
                triggered = self.kb.waitForTrigger(skip=skip-1)
                if triggered:
                    self.triggerCnt = self.kb.triggerCnt
                    self._lastTriggerTime = self.kb.triggerTime
                else:
                    return False
            except RuntimeError as e:
                logging.error('Could not initialize trigger LAUNCHSCAN')
                raise e
        return True

    def getTrigger(self):
        """Checks if a trigger has been received for LaunchScanTrigger.

        Returns:
            True if trigger detected, False if none detected.
        """
        self._trigger = self.kb.getTrigger()
        if self._trigger:
            self.triggerCnt += 1
            self._dtime = self.kb.triggerTime
            self._lastTriggerTime = self._dtime
        return self._trigger


####################################################################
# CEDRUS                                                           #
####################################################################

class CedrusTrigger(DeviceTrigger):
    """Cedrus device XID trigger.

    Wrapper for the Cedrus device (pyxid).
    """

    _PORTTYPE = 'CEDRUS'

    def __init__(self, win, globalClock, portConfig=None, **kwargs):
        """Constructor of CedrusTrigger.

        Args:
            win: psychopy.visual.Window object
            globalClock: global clock object (required)

        Keyword args:
            portConfig: dictionary with keys
                device: device number of Xid device (default: 0)
                sync: extra argument - sync value (default: 4)
            timeout: timeout value (in seconds) to abort waiting the start
                of a scan
            esc_key: keyboard key value to abort waiting the start of
                a scan manually
            device: fully configured pyxdid.XidDevice object.
                If provided, all device-specific settings in portConfigKeyList
                will be ignored.

        Exception:
            Raises a DeviceTriggerException when no port is defined
            (a port name or a serial port device).

        Remark: timeout value of pyserial is ignored to ignore blocking.

        More info: http://pyserial.readthedocs.io/en/latest/pyserial_api.html
        """
        # Configure key lists
        portConfigKeyList = ['devicenr']
        extraConfigKeyList = ['sync', ]

        # Base class constructor
        super(CedrusTrigger, self).__init__(
                globalClock, portConfig, portConfigKeyList,
                extraConfigKeyList, **kwargs)

        # Configure default values
        if 'devicenr' not in self._portArgs:
            self._portArgs.update({'devicenr': 0})

        if 'sync' not in self.extraArgs:
            self.extraArgs.update({'sync': 4})

        if 'device' in self.extraArgs:
            if isinstance(self.extraArgs['device'], pyxid.XidDevice):
                self._port = self.extraArgs['device']

        if self._port is None:
            logging.log('Created trigger SERIAL: ' +
                        str(self._portArgs) + str(self.extraArgs),
                        self.logLevel)
        else:
            logging.log('Created trigger SERIAL: ' + str(self._port),
                        self.logLevel)

    def open(self):
        """Initialization of CedrusTrigger.

        Exception:
            Raises a DeviceTriggerException if port could not be opened.
        """
        try:
            if self._port is None:
                logging.log('Detecting Cedrus XID devices', self.logLevel)
                devlist = pyxid.get_xid_devices()
                self._port = devlist[0]
                # pyxid.get_xid_device(self._portArgs['devicenr'])
            else:
                pass
            logging.log('Opened Cedrus XID device ' +
                        str(self._port), self.logLevel)
        except ValueError as e:
            logging.error('Could not open Cedrus XID device ' +
                          str(self._portArgs['devicenr']))
            raise portNotOpenError

        super(CedrusTrigger, self).open()

    def close(self):
        """Closing and cleanup of CedrusTrigger."""
        # if type(self._port) is serial.Serial:
        #     self._port.close()
        super(CedrusTrigger, self).close()

    def getTrigger(self):
        """Checks if a trigger has been received for CedrusTrigger.

        Only detects the first trigger in the queue, the rest is ignored!

        Returns:
            True if trigger detected, False if none detected.
        """

        self._trigger = False

        # check for key presses
        self._port.poll_for_response()
        while len(self._port.response_queue):
            evt = self._port.get_next_response()
            if evt['key'] not in [self.extraArgs['sync']]:
                continue  # we don't care about this key

            if evt['pressed']:
                # Only detect the first press, skip the others
                self._trigger = True
                self._dtime = self.globalClock.getTime()
                break
            self._port.poll_for_response()
        self._port.clear_response_queue()  # don't process again

        return self._logTrigger()

    def waitForTrigger(self, skip=0):
        # Clear the queue first, then use the standard function
        self._port.poll_for_response()
        while len(self._port.response_queue):
            self._port.clear_response_queue()
            self._port.poll_for_response()
        return super(CedrusTrigger, self).waitForTrigger(skip)
