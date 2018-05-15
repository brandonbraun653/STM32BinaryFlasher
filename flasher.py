import sys
import os
import subprocess

error = 'Couldn\'t find any ST-Link/V2 devices'

stm32f7_binary_dir = 'TestBinaries/STM32F7xxx'


class STM32BinaryFlasher():
    # Add more as needed
    

    def __init__(self, binaries_dir):
        self.binary_root = binaries_dir
        self.device = {}

        self.no_dev_err = 'Found 0 stlink programmers\n'

        self.supported_devices = \
        {
            # Device Name : Device ID
            "STM32F76xx": 0x0451,
            "STM32F77xx": 0x0451,
            "STM32F446xx": 0x0421
        } 
    
    def _device_from_id(self, id):
        return list(self.supported_devices.keys())[list(self.supported_devices.values()).index(id)]

    def _index_of_substring(self, string_list, substring):
        for i, s in enumerate(string_list):
            if substring in s:
                return i
        return -1

    def _clean_probe(self, raw_output):
        # Clean up the raw string from the probe cmd result
        probe_data = raw_output.stdout.decode("utf-8").split('\n')
        probe_data = [x.strip() for x in probe_data]

        # Check for a valid device found 
        self.device["probe_msg"] = probe_data[0]
        if self.no_dev_err in self.device["probe_msg"]:
            return

        # Grab the chip-id
        string = probe_data[self._index_of_substring(probe_data, 'chipid')].split(" ")
        self.device["chip_id"] = int(string[1], 16)

    
    def check_connection(self, expected_device):
        if expected_device not in self.supported_devices.keys():
            print("Unrecognized device type, exiting.")
            return False

        self._clean_probe(subprocess.run("st-info --probe", shell=True, stdout=subprocess.PIPE))

        if self.no_dev_err in self.device["probe_msg"]:
            print("ST-Link Device Not Found")
            return False
        
        elif self.device["chip_id"] != self.supported_devices[expected_device]:
            actual_device = self._device_from_id(self.device["chip_id"])
            print("Connected to an " + actual_device + " instead of an " + expected_device)

        else:
            print("Successfully connected to an " + expected_device)
            return True

    def flash_device(self, binary_file, address):
        flash_cmd = " ".join(["st-flash write", os.path.join(self.binary_root, binary_file), address]) 

        print(flash_cmd)
        output = subprocess.run(flash_cmd, shell=True)

        if output.returncode != 0:
            raise RuntimeError("Failed flashing \'" + binary_file + "\' at location \'" + address + "\'")

if __name__ == "__main__":
    flasher = STM32BinaryFlasher(stm32f7_binary_dir)

    flasher.check_connection("STM32F76xx")
    flasher.flash_device("ChimeraDevelopment.bin", "0x80000000")