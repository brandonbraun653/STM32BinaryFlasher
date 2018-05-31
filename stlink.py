import sys
import os
import re
import subprocess




class STLink_USBInterface:
    """
    A lower level object that is intended to provide an OS independent (between Windows/Linux)
    interface for finding and gathering information on connected STLink programmers.
    """
    STLINK_VENDOR_ID = '0483'

    STLINK_TYPES = [
        {
            'version': 'V2',
            'idVendor': 0x0483,
            'idProduct': 0x3748,
            'outPipe': 0x02,
            'inPipe': 0x81,
        }, {
            'version': 'V2-1',
            'idVendor': 0x0483,
            'idProduct': 0x374b,
            'outPipe': 0x01,
            'inPipe': 0x81,
        }
    ]

    def __init__(self):
        # Container holding gathered device data
        self.stlink_devices = []
        self.usb_devices = None

        # The loaded device to be used for all attributes
        self.attached_device = {}

    def discover_devices(self, core_filter=None, chip_filter=None):
        """
        Finds all connected STLink devices and populates information about them
        :param core_filter:
        :param chip_filter:
        :return:
        """

        # First let the STLink firmware discover devices
        self._stlink_probe()

        if self.stlink_devices:

            # Grab lower level information about the USB devices (port, devid, etc)
            self._get_usb_devices()

            # Use the information from STLink and USB to build a more complete picture
            # of which device is on which port
            self._assign_port_to_device()

            print(self._get_port_from_serial(self.stlink_devices[0]['serial']))

    def save_device(self, name, device_data, filename):
        pass

    def _get_usb_devices(self):
        """
        Finds all the connected usb devices on the computer and reports them back in a neat dictionary
        Courtesy of:
            1) https://goo.gl/m52UG7
            2) https://goo.gl/yXziE6
        """

        # Get every device on the bus
        device_re = re.compile("Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
        df = subprocess.check_output("lsusb")
        devices = []

        for i in df.decode().split('\n'):
            if i:
                info = device_re.match(i)
                if info:
                    dinfo = info.groupdict()
                    dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                    devices.append(dinfo)

        # Filter only for the STLink devices
        st_link_devices = []
        for device in devices:
            if self.STLINK_VENDOR_ID in device['id']:
                st_link_devices.append(device)

        self.usb_devices = st_link_devices

    def _stlink_probe(self):
        """
        Utilizes the open source stlink software to probe for connected STLink programmers. Should any be
        found, they are added to the class as a discovered device.
        """
        raw_output = subprocess.run("st-info --probe", shell=True, stdout=subprocess.PIPE)

        # Clean up the raw string from the probe cmd result
        probe_data = raw_output.stdout.decode("utf-8").split('\n')
        probe_data = [x.strip() for x in probe_data]
        probe_data = list(filter(None, probe_data))

        # The first line returns if a programmer was found and how many
        if probe_data[0] != "Found 0 stlink programmers":
            total_found = int(probe_data[0].split(' ')[1])
            del probe_data[0]

            # Gather all the characteristics for the discovered devices
            for i in range(0, total_found):
                self.stlink_devices.append({})

                # Info is given in blocks of 6 lines that must be parsed
                offset = i*6
                device_data = probe_data[0+offset:6+offset]

                for field in device_data:
                    data = field.split(' ')
                    self.stlink_devices[i][data[0].strip(':')] = data[1]

                # Apply special filtering to known probe return values
                self.stlink_devices[i]['serial']  = int(self.stlink_devices[i]['serial'])
                self.stlink_devices[i]['flash']   = int(self.stlink_devices[i]['flash'])
                self.stlink_devices[i]['sram']    = int(self.stlink_devices[i]['sram'])
                self.stlink_devices[i]['chipid']  = int(self.stlink_devices[i]['chipid'], 16)

                self.stlink_devices[i]['openocd'] = self.stlink_devices[i]['openocd'].strip('\"')
                self.stlink_devices[i]['openocd'] = self.stlink_devices[i]['openocd'].replace('\\x', '')

    def _assign_port_to_device(self):
        """
        Pairs discovered STLink programmers with the correct USB port/bus
        :return:
        """
        for i in range(0, len(self.stlink_devices)):
            self.stlink_devices[i]['usb_port'] = self._get_port_from_serial(self.stlink_devices[i]['serial'])

    def _get_port_from_serial(self, serial):
        assert(isinstance(serial, int))

        # Make sure the STLink devices are discovered
        self._get_usb_devices()

        for usb_device in self.usb_devices:
            port_split = list(filter(None, usb_device["device"].split('/')))
            usb_bus = port_split[3]
            usb_addr = port_split[4]

            if serial == self._get_serial_number(usb_bus, usb_addr):
                return usb_bus + ":" + usb_addr

    def _get_serial_number(self, bus, addr):
        """
        Gets the serial number of an STLink device on a given USB bus and address in the format <BUS>:<ADDR>
        :return: (int) serial number
        """
        command = "export STLINK_DEVICE=" + str(bus) + ":" + str(addr) + "; st-info --serial"
        raw_output = subprocess.run(command, shell=True, stdout=subprocess.PIPE)

        return int(raw_output.stdout.decode('utf-8').strip('\n'))




# Will need to set the environment variable for programming

class STLink:
    """
    High level interface to an STLink device that defines commonly used operations
    """
    def __init__(self, usb_interface):
        pass

    def get_version(self):
        pass

    def erase(self, start_addr=None, end_addr=None):
        # Remember to do a full erase if no params
        pass

    def flash(self, binary_file, address):
        pass

    def reset(self):
        pass


if __name__ == "__main__":
    dev = STLink_USBInterface()

    dev.discover_devices()
    print(dev.stlink_devices[0])
    print(dev.stlink_devices[1])

