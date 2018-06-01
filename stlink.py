import sys
import os
import re
import json
import subprocess


class STLink_USBInterface:
    """
    A lower-ish level object that is intended to provide an OS independent (between Windows/Linux)
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
        self.stlink_devices = []
        self.usb_devices = None
        self.attached_device = {}

    def discover_devices(self):
        """
        Finds all connected STLink devices and populates information about them into the
        class self.stlink_devices list.
        """
        # First let the STLink firmware discover devices
        self._stlink_probe()

        if self.stlink_devices:
            print("Discovered %d STLink device(s)." % len(self.stlink_devices))

            # Grab lower level information about the USB devices (port, dev-id, etc)
            self._get_usb_devices()

            # Use the information from STLink probe and USB to build a more complete picture
            # of which device is on which port
            self._assign_port_to_device()

        else:
            print("No STLink devices were discovered.")

    def save_device(self, name, filename):
        """
        Saves an attached device settings to file
        :param name: A unique friendly name for this device
        :param filename: where to save the file (must include .json extension)
        """
        if self.attached_device:
            self.attached_device['name'] = name

            if filename.endswith(".json"):
                with open(filename, 'w') as file:
                    json.dump(self.attached_device, file)
            else:
                raise ValueError("Could not save file. Expected a .json extension.")

        else:
            print("No device attached to the USB interface. Nothing to save!")

    def load_device(self, filename):
        """
        Loads a previously saved device settings json file
        :param filename: Location of the settings file
        """

        if filename.endswith(".json"):
            with open(filename) as file:
                self.attached_device = json.loads(file.read())

            print("Loaded device: %s" % self.attached_device["name"])
        else:
            raise ValueError("Cannot load file. Expected a .json extension.")

    def attach_device(self, device_data):
        """
        Assigns a specific instance of a discovered device as the class default device
        :param device_data: One of the devices from found_devices()
        """
        self.attached_device = device_data

    def get_port_from_serial(self, serial):
        assert(isinstance(serial, int))

        # Make sure the STLink devices are discovered
        self._get_usb_devices()

        for usb_device in self.usb_devices:
            # The port is listed as "/~/~/bus/addr
            port_split = list(filter(None, usb_device["device"].split('/')))
            usb_port = port_split[3] + ":" + port_split[4]

            if serial == self.get_serial_number(usb_port):
                return usb_port

        return None

    def get_serial_number(self, port):
        """
        Gets the serial number of an STLink device on a given USB bus and address in the format <BUS>:<ADDR>
        :return: (int) serial number
        """
        command = "export STLINK_DEVICE=" + port + "; st-info --serial"
        raw_output = subprocess.run(command, shell=True, stdout=subprocess.PIPE)

        if raw_output.returncode == 0:
            return int(raw_output.stdout.decode('utf-8').strip('\n'))
        else:
            return -1

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
        found, they are added to the class as a discovered device. Unfortunately no information about the
        USB bus they are connected to is given, so use _get_usb_devices() for that.
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

                # Info is given in repeating blocks of 6 lines that must be parsed
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
        Pairs discovered STLink programmers with the correct USB port/bus in the device dictionary
        """
        for i in range(0, len(self.stlink_devices)):
            self.stlink_devices[i]['usb_port'] = self.get_port_from_serial(self.stlink_devices[i]['serial'])

    @property
    def port(self):
        return self.attached_device['usb_port']

    @property
    def name(self):
        return self.attached_device['name']

    @property
    def serial_number(self):
        return self.attached_device['serial']

    @property
    def chip_id(self):
        return self.attached_device['chipid']

    @property
    def found_devices(self):
        return self.stlink_devices


class STLink:
    """
    High level interface to an STLink device that defines commonly used operations
    """
    def __init__(self, usb_dev):
        # Make sure the USB port recorded in the interface matches the recorded serial number
        if usb_dev.serial_number != usb_dev.get_serial_number(usb_dev.port):
            print("Device %s not found. Previously used on port %s." % (usb_dev.name, usb_dev.port))
            usb_dev.attached_device['usb_port'] = usb_dev.get_port_from_serial(usb_dev.serial_number)

            if not usb_dev.port:
                raise ConnectionError("Device %s has disappeared! Where did it go?" % usb_dev.name)

            print("Device %s rediscovered on port %s." % (usb_dev.name, usb_dev.port))


        self.stlink = usb_dev

    def erase(self):
        """
        Performs a mass erase on the attached STLink device
        """
        command = "export STLINK_DEVICE=" + self.stlink.port + "; st-flash erase"
        subprocess.run(command, shell=True)

    def flash(self, binary_file, link_address="0x08000000"):
        """
        Flashes the attached STLink device
        :param binary_file: absolute path to the binary to be flashed
        :param link_address: program flash link address, defaults to 0x08000000
        """
        command = "export STLINK_DEVICE=" + self.stlink.port + "; st-flash write " + binary_file + " " + link_address
        subprocess.run(command, shell=True)

    def reset(self):
        """
        Resets the attached STLink device
        """
        command = "export STLINK_DEVICE=" + self.stlink.port + "; st-flash reset"
        subprocess.run(command, shell=True)


if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))

    usb = STLink_USBInterface()

    #usb.discover_devices()
    #usb.attach_device(usb.found_devices[0])
    #usb.save_device("stm32f767zit", "test.json")
    usb.load_device("test.json")

    stlink = STLink(usb)
    #stlink.reset()
    #stlink.erase()
    stlink.flash(os.path.join(dir_path, "TestBinaries/STM32F7xxx/ChimeraDevelopment.bin"))


