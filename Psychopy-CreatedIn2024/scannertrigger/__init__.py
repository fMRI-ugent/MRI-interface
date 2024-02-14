"""This is the ScannerTrigger module.

This module is a wrapper class for all devices which can detect a trigger from
the MR scanner to PsychoPy.
It aims to implement a uniform interface accross devices.
Currently supported devices are
    * Serial port (pyserial module)
    * Parallel port (psychopy.parallel module)
    * Keyboard (psychopy.event module)
    * LaunchScan (psychopy.hardware.emulator and psychopy.event modules)
    * Dummy (emulates a keyboard event every n seconds with millisecond
      accuracy)
Other devices may be added in the future.

For detailed information and an example, see the README.TXT file shipped with
this module.
"""

import scannertrigger.devicetrigger as dt

__version__ = '0.1'
__author__ = 'Pieter Vandemaele'

RISING = 1
FALLING = -1
BOTH = 0


class ScannerTrigger(object):
    """Class implementing a factory method to return the requested device.

    Currently implemented devices can be listed as follows:

    >>> import devicetrigger as dt
    >>> print(dt.DeviceTrigger.registry)

    """

    @staticmethod
    def _factory(win, globalClock, portType, portConfig=None, **kwargs):
        """ Factory function which creates and initializes a trigger device"""

        port = portType.lower()

        if port in dt.DeviceTrigger.registry:
            return dt.DeviceTrigger.registry[port](
                win, globalClock, portConfig, **kwargs)

        raise ValueError('Cannot connect to {}'.format(portType))

    @staticmethod
    def create(win, globalClock, portType, portConfig=None, **kwargs):
        """ Main function to create a trigger device

        """
        trigger = None

        try:
            trigger = ScannerTrigger._factory(
                win, globalClock, portType, portConfig, **kwargs)
        except ValueError as ve:
            logging.error(ve)

        return trigger


if __name__ == '__main__':
    print("For detailed information and an example, " +
          "see the README.TXT file shipped with this module.")
    pass
