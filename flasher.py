import sys
import subprocess

flash_cmd = "st-flash write ChimeracDevelopment.bin 0x08000000"

error = 'Couldn\'t find any ST-Link/V2 devices'

def check_connection():
    expected_error_msg = 'Found 0 stlink programmers\n'
    output = subprocess.run("st-info --probe", shell=True, stdout=subprocess.PIPE)

    return_string = output.stdout.decode("utf-8").split('\n')
    return_string = [x.strip() for x in return_string]
    print(return_string)

    if expected_error_msg in return_string:
        print("ST-Link Device Not Found")
    else:
        print("Yay device found!")

def flash_device():
    output = subprocess.run(flash_cmd, shell=True)

if __name__ == "__main__":
    check_connection()