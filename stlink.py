import sys
import os
import subprocess




class STLink_USBInterface:
    """
    A lower level object that is intended to provide an OS independent (between Windows/Linux)
    interface for finding and gathering information on connected STLink programmers.
    """
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
        self.device = {}

        self.usb_port = None

    def discover_devices(self, core_filter=None, chip_filter=None):
        """
        Finds all connected ST
        :param core_filter:
        :param chip_filter:
        :return:
        """
        self._probe()

    def attach_to_device(self, full_chip_id):
        # The idea here is to automatically find a specific device, whatever the port, and
        # then save all the information to it.
        pass

    def _probe(self):
        self._parse_probe(subprocess.run("st-info --probe", shell=True, stdout=subprocess.PIPE))

    def _index_of_substring(self, string_list, substring):
        for i, s in enumerate(string_list):
            if substring in s:
                return i
        return -1

    def _parse_probe(self, raw_output):
        # Clean up the raw string from the probe cmd result
        probe_data = raw_output.stdout.decode("utf-8").split('\n')
        probe_data = [x.strip() for x in probe_data]

        print(probe_data)

        # The first line returns if a programmer was found
        self.device["probe_msg"] = probe_data[0]

        # TODO: Encapsulate in IF statement to handle case where no programmer is found

        for field in probe_data[1:]:
            data = field.split(' ')

            if data[0]:
                self.device[data[0].strip(':')] = data[1]
                print(data)

        # Apply special filtering to known probe values. Mostly this is just converting
        # strings to integers
        self.device['serial'] = int(self.device['serial'])
        #self.device['openocd'] = int(self.device['openocd'], 16)
        self.device['flash'] = int(self.device['flash'])
        self.device['sram'] = int(self.device['sram'])
        self.device['chipid'] = int(self.device['chipid'], 16)







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
    print(dev.device)