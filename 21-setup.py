import sys
import os.path
import json
import time
import logging
import base64
import subprocess
import tempfile
import glob
import errno
import platform
import codecs
import getpass
import re
import random
import string

if sys.platform.startswith("win"):
    # Use pyserial on windows
    import serial
    import serial.tools.list_ports
else:
    import termios

if sys.version_info.major > 2:
    # Python 3
    from urllib.request import FancyURLopener
    raw_input = input
else:
    # Python 2
    from urllib import FancyURLopener


class AppURLopener(FancyURLopener):
    # Add User-agent otherwise Cloudflare gets angry
    version = 'Mozilla/5.0'

urlretrieve = AppURLopener().retrieve


# Version

__version__ = "11-05-2015-04:45:00"


# Logger (for debug)

logger = logging.getLogger(__name__)


# Print helper functions

def print_step(s):
    if sys.platform.startswith("win"):
        print(s)
    else:
        print("\x1b[1;35m" + s + "\x1b[0m")


def print_warning(s):
    if sys.platform.startswith("win"):
        print(s)
    else:
        print("\x1b[1;33m" + s + "\x1b[0m")


def print_error(s):
    if sys.platform.startswith("win"):
        print(s)
    else:
        print("\x1b[1;31m" + s + "\x1b[0m")


# Serial class

class Serial:

    def __init__(self, path):
        """Open serial port at specified device path with baudrate 115200, and
        8N1."""

        self.fd = None
        self.ser = None
        self.open(path)

    def open(self, path):
        """Open serial port at specified device path with baudrate 115200, and
        8N1."""

        if sys.platform.startswith("win"):
            if 'serial' in globals():
                self.ser = serial.Serial(path, 115200, timeout=0.25)
            self.ser.flushInput()
            return

        # Open the serial port
        try:
            self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        except OSError as e:
            raise Exception("Opening serial port: {}".format(str(e)))

        # Configure serial port to raw, 115200 8N1
        tty_attr = termios.tcgetattr(self.fd)
        tty_attr[0] = termios.IGNBRK    # iflag
        tty_attr[1] = 0                 # oflag
        tty_attr[2] = termios.CREAD | termios.CLOCAL | termios.B115200 | termios.CS8  # cflag
        tty_attr[3] = 0                 # lflag
        tty_attr[4] = termios.B115200   # ispeed
        tty_attr[5] = termios.B115200   # ospeed

        try:
            termios.tcsetattr(self.fd, termios.TCSANOW, tty_attr)
        except OSError as e:
            raise Exception("Configuring serial port: {}".format(str(e)))

    def set_timeout(self, timeout):
        if sys.platform.startswith("win"):
            self.ser.timeout = timeout

    def read(self, n, timeout=None):
        """Read up to n bytes from the serial port, or until specified timeout
        in seconds.

        Args:
            n (int): number of bytes to read
            timeout (None or int): read timeout

        Returns:
            bytes: data read

        """

        if sys.platform.startswith("win"):
            return self.ser.read(n)

        buf = b""

        tic = time.time()
        while len(buf) < n:
            try:
                buf += os.read(self.fd, n - len(buf))
            except OSError as e:
                if e.errno != errno.EAGAIN:
                    raise e
                time.sleep(0.01)

            if timeout and (time.time() - tic) > timeout:
                break

        return buf

    def readline(self):
        """Read a line from the serial port up to \r or \n.

        Returns:
            bytes: line read, without the newline delimiter

        """

        if sys.platform.startswith("win"):
            return self.ser.readline()

        buf = b""

        while True:
            try:
                c = os.read(self.fd, 1)
            except OSError as e:
                if e.errno != errno.EAGAIN:
                    raise e
                time.sleep(0.01)
                continue

            if c in [b"\r", b"\n"]:
                if len(buf):
                    break
                else:
                    continue

            buf += c

        return buf

    def write(self, data):
        """Write data to serial port.

        Args:
            data (bytes): data to write

        """

        if sys.platform.startswith("win"):
            self.ser.write(data)
            return

        os.write(self.fd, data)

    def flush_input(self):
        """Flush input buffer on serial port."""

        if sys.platform.startswith("win"):
            self.ser.flushInput()
            return

        termios.tcflush(self.fd, termios.TCIFLUSH)

    def flush_output(self):
        """Flush output buffer on serial port."""

        if sys.platform.startswith("win"):
            self.ser.flushOutput()
            return

        termios.tcdrain(self.fd)

    def writeline(self, line, wait_time=0.5):
        """Write a line to the serial port. This mimics a user typing in a line and
        pressing enter.

        Args:
            line (str): Line to write
            wait_time (float): Time to wait in seconds after writing the line

        """

        if sys.platform.startswith("win"):
            if isinstance(line, str):
                self.ser.write(line.encode() + b"\r\n")
            else:
                self.ser.write(line + b"\r\n")
            self.ser.flush()
            time.sleep(wait_time)
            return

        if isinstance(line, str):
            self.write(line.encode() + b"\r\n")
        else:
            self.write(line + b"\r\n")

        self.flush_output()
        time.sleep(wait_time)

    def close(self):
        """Close the serial port."""

        if sys.platform.startswith("win"):
            self.ser.close()
            return

        os.close(self.fd)
        self.fd = None


# Cmdmule script and command wrapper

CMDMULE_SCRIPT = b"""
import sys
import json
import subprocess

print("cmdmule started")
try:
    while True:
        s = sys.stdin.readline().strip()
        if len(s) == 0:
            continue

        cmd = json.loads(s)

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        result = {'returncode': p.returncode, 'stdout': p.stdout.read().decode(
            "ascii", "ignore"), 'stderr': p.stderr.read().decode("ascii", "ignore")}

        sys.stdout.write(json.dumps(result) + '\\n')
except KeyboardInterrupt:
    sys.exit(0)
"""
"""The cmdmule script is loaded onto the target over the serial port and run in
task_cmdmule(). This script listens for commands over the serial port, executes
them, and responds with a JSON object containing the resulting return code,
stdout, and stderr. This simplifies remote command execution over the serial
port, as it propagates the return code of commands, properly escapes newlines
in stderr and stdout, and removes the bash prompt from the serial output."""


def cmdmule_command(ser, cmd):
    """Execute a command over the serial port in a running cmdmule.

    Args:
        ser (Serial): Serial port object
        cmd (str): Command to execute

    Returns:
        dict: Dictionary containing returncode, stdout, stderr keys.

    """

    # Write command
    ser.flush_input()
    ser.write(json.dumps(cmd).encode() + b"\n")

    # Read command sent
    ser.readline()
    # Read result
    result = ser.readline()

    # Decode result
    return json.loads(result.strip().decode("ascii", "ignore"))


# Setup tasks

def task_assert_host():
    """This task asserts this script is running on a host computer instead of
    the Bitcoin Computer."""

    if os.path.exists("/etc/21-release"):
        print_error("Error: This script should be run on a host computer "
                    "connected to the Bitcoin Computer with a USB to serial cable.")
        sys.exit(1)


def task_install_serial_driver():
    """This task install the PL2303 driver on Mac OS X, if it isn't
    installed."""

    PL2303_KEXT_PATH1 = "/System/Library/Extensions/ProlificUsbSerial.kext"
    PL2303_KEXT_PATH2 = "/Library/Extensions/ProlificUsbSerial.kext"
    PL2303_DRIVER_NEW = (
        "https://install.21.co/PL2303_MacOSX-Driver_1_6_0_20151012.zip",
        "PL2303_1.6.0_20151012.pkg"
    )
    PL2303_DRIVER_OLD = (
        "https://install.21.co/md_PL2303_MacOSX_10_6-10_10_v1_5_1.zip",
        "PL2303_MacOSX_v1.5.1.pkg"
    )

    # Install the PL2303 on Mac OS X, if it isn't installed
    if sys.platform.startswith("darwin") and \
            (not os.path.exists(PL2303_KEXT_PATH1) and not os.path.exists(PL2303_KEXT_PATH2)):
        print_step("Installing PL2303 USB serial port driver...")

        # Pick the correct driver based on OS X version
        if tuple(int(x) for x in platform.mac_ver()[0].split(".")) >= (10, 9, 0):
            driver_url, driver_pkg = PL2303_DRIVER_NEW
        else:
            driver_url, driver_pkg = PL2303_DRIVER_OLD

        # Fetch the driver
        print_step("\nFetching driver from {} ...".format(driver_url))
        try:
            def urlretrieve_report_hook(count, block_size, total_size):
                BAR_WIDTH = 80
                count += 1
                sys.stdout.write("\r|")
                sys.stdout.write("=" * int(BAR_WIDTH * (count * block_size) / total_size))
                sys.stdout.write(" " * int(BAR_WIDTH - BAR_WIDTH * (count * block_size) / total_size))
                sys.stdout.write("| {}%".format(int(100.0 * (count * block_size) / total_size)))

            zippath, _ = urlretrieve(driver_url, reporthook=urlretrieve_report_hook)
            sys.stdout.write("\n")
        except Exception as e:
            raise Exception("Fetching PL2303 driver: {}".format(str(e)))

        # Unzip the driver to a temporary directory
        print_step("\nExtracting driver...")
        tmpdir = tempfile.mkdtemp()
        try:
            subprocess.check_output("unzip -q -d {} {}".format(tmpdir, zippath), shell=True)
        except subprocess.CalledProcessError as e:
            raise Exception("Extracting PL2303 driver: {}\n{}".format(str(e), e.output))

        # Install the driver
        print_step("\nInstalling driver... Please enter system password if prompted.")
        pkgpath = tmpdir + "/" + driver_pkg
        print("sudo installer -verboseR -pkg {} -target /".format(pkgpath))
        try:
            subprocess.check_output("sudo installer -verboseR -pkg {} -target /".format(pkgpath),
                                    stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            raise Exception("Installing PL2303 driver: {}\n{}".format(str(e), e.output))

        print_step("\nDriver successfully installed!")

        # Load the kernel extension
        print_step("\nRebooting system..")
        try:
            subprocess.check_output(
                "osascript -e 'tell app \"loginwindow\" to \xc2\xabevent aevtrrst\xc2\xbb'",
                stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            raise Exception("Rebooting system: {}\n{}".format(str(e), e.output))

        sys.exit(0)


def task_find_serial_port():
    """This task finds and open the USB serial port.

    Returns:
        Serial: Serial port object

    """

    while True:
        if sys.platform.startswith("darwin"):
            if os.path.exists("/dev/tty.usbserial"):
                port = "/dev/tty.usbserial"
                break

        elif sys.platform.startswith("win"):
            ports = list(serial.tools.list_ports.grep('Prolific'))
            if len(ports) > 0:
                port = ports[0][0]
                break
        else:
            # Get a list of /dev/ttyUSB* candidates
            tty_ports = glob.glob("/dev/ttyUSB*")

            def map_vid_pid(tty_port):
                tty_name = os.path.basename(tty_port)

                try:
                    # Read VID
                    with open("/sys/bus/usb-serial/devices/{}/../../idVendor".format(tty_name)) as f:
                        vid = int(f.read().strip(), 16)
                    # Read PID
                    with open("/sys/bus/usb-serial/devices/{}/../../idProduct".format(tty_name)) as f:
                        pid = int(f.read().strip(), 16)
                except Exception:
                    return (None, None)

                return (vid, pid)

            # Map (vid, pid) to each /dev/ttyUSBX
            tty_ports = {tty_port: map_vid_pid(tty_port) for tty_port in tty_ports}
            # Filter by Prolific (vid, pid)
            tty_ports = [tty_port for tty_port in tty_ports if tty_ports[tty_port] in [(0x067b, 0x2303)]]

            if len(tty_ports) > 0:
                # Pick first port
                port = tty_ports[0]
                break

        print_warning("Please connect the USB serial port cable to the Bitcoin Computer.")
        print_warning("Press enter to continue.")
        raw_input()

    return Serial(port)


def task_prompt(ser):
    """This task restores the target to the login prompt.

    Args:
        ser (Serial): Serial port object

    """

    while True:
        # Get an idea of where we're at
        ser.writeline("\x03\x03\x03\n\n")
        buf = ser.read(2048, timeout=0.50).decode("ascii", "ignore")

        if "Raspbian GNU/Linux 8" in buf:
            # At the login prompt
            logger.debug("[login_prompt] at login prompt")
            break
        elif "root@" in buf and "#" in buf:
            # At the command line
            logger.debug("[login_prompt] at command line")
            ser.writeline("exit")

    ser.flush_input()


def task_login(ser):
    """This task logins in under user root from the login prompt.

    Args:
        ser (Serial): Serial port object

    """

    # Login
    print_step("\nLogging into the Bitcoin Computer...")
    ser.writeline("root")
    ser.writeline("root")

    # Look for command line
    buf = ser.read(2048, timeout=1.00).decode("ascii", "ignore")
    if not ("root@" in buf and "#" in buf):
        raise Exception("Failed to login.")

    logger.debug("[login] logged in")

    ser.flush_input()


def task_cmdmule(ser):
    """This task ships over and starts the cmdmule script on the target.

    Args:
        ser (Serial): Serial port object

    """

    # Base64 encode cmdmule script
    cmdmule_script = base64.b64encode(CMDMULE_SCRIPT) + b"\n" + b"\x04"

    # Write it to /tmp/cmdule.py
    logger.debug("[cmdmule] sending cmdmule script")
    ser.writeline("base64 -d > /tmp/cmdmule.py")
    ser.writeline(cmdmule_script)

    # Start running it
    logger.debug("[cmdmule] starting cmdmule script")
    ser.writeline("python3 /tmp/cmdmule.py")

    # Check that it started
    buf = ser.read(2048, timeout=1.00).decode("ascii", "ignore")
    if "cmdmule started" not in buf:
        raise Exception("Failed to start cmdmule script.")

    logger.debug("[cmdmule] cmdmule started")

    # Disable timeout on serial port for Windows now, as we'll be reading until
    # newline with cmdmule
    ser.set_timeout(None)

    ser.flush_input()


def task_connect_wifi(ser):
    """This task scans for WiFi networks, prompts the user to pick one, and
    configures the wireless interface with WPA1/2 PSK, or skips the process
    entirely if the wireless interface is not available and the user decides to
    use Ethernet.

    Args:
        ser (Serial): Serial port object

    """

    print_step("\nSetting up WiFi...\n")

    while True:
        # Look up wlan interface
        result = cmdmule_command(ser, "ifconfig -a | grep -o \"wlan[0-9]\"")
        if result['returncode'] != 0:
            print_warning("WiFi dongle not found. Please connect the WiFi dongle and press enter.")
            print_warning("Alternatively, type \"skip\" to use Ethernet.")
            if raw_input() == "skip":
                break
            continue
        wlan_interface = result['stdout'].strip()

        logger.debug("[connect_wifi] wlan interface is %s", wlan_interface)

        # Start wpa_supplicant in control interface mode, if it's not already running
        if cmdmule_command(ser, "sudo wpa_cli status")['returncode'] != 0:
            result = cmdmule_command(
                ser, "sudo wpa_supplicant -B -i {0} -D wext -C /run/wpa_supplicant".format(wlan_interface))
            if result['returncode'] != 0:
                raise Exception("Failed to start wpa_supplicant: {}".format(result['stderr']))

        # Disable the active network, so we can scan
        cmdmule_command(ser, "sudo wpa_cli disable_network 0")
        time.sleep(1)

        # Scan for wireless networks
        print_step("Scanning for WiFi networks...")
        cmdmule_command(ser, "sudo wpa_cli scan")
        # Give scan some time to complete
        time.sleep(3)

        # Get latest scan results
        results = cmdmule_command(ser, "sudo wpa_cli scan_results")

        # Split wireless networks results by newline
        wifi_networks = results['stdout'].strip().split("\n")

        # Check we got at least one wireless network
        if len(wifi_networks) < 3:
            raise Exception("No wireless networks found.")

        # Strip off heading
        wifi_networks = wifi_networks[2:]
        # Split network info
        wifi_networks = [x.split("\t") for x in wifi_networks]
        # Format network info into dictionary
        wifi_networks = [
            {
                "bssid": n[0],
                "frequency": n[1],
                "strength": n[2],
                "flags": n[3],
                "ssid": n[4] if len(n) > 4 else ""
            } for n in wifi_networks
        ]
        # Filter out non-empty ssid
        wifi_networks = list(filter(lambda network: network["ssid"], wifi_networks))
        # Filter out subsequent duplicate ssids
        unique_wifi_networks = []
        for network in wifi_networks:
            if network["ssid"] not in [n["ssid"] for n in unique_wifi_networks]:
                unique_wifi_networks.append(network)

        # Print list of wireless networks for user to choose
        print("\nWiFi Networks")
        print("")
        for i in range(len(unique_wifi_networks)):
            print("    {:>2} - {}".format(i + 1, unique_wifi_networks[i]['ssid']))
        print("")

        # Get wireless network information from user
        while True:
            print_step("Please choose the same WiFi network as your personal computer.")
            print_step("")
            wifi_network_index = raw_input("    WiFi Network Number: ")
            password = getpass.getpass("    WiFi WPA1/2 Passphrase (if any): ")

            # Convert network index to int
            try:
                wifi_network_index = int(wifi_network_index) - 1
            except ValueError:
                print_error("\nInvalid network number!\n")
                continue

            # Check network index is in range
            if wifi_network_index not in range(len(unique_wifi_networks)):
                print_error("\nNetwork number out of bounds!\n")
                continue

            break

        # Unescape any characters in the SSID (escaped by wpa_cli)
        ssid = re.sub(r"\\(.)", "\g<1>", unique_wifi_networks[wifi_network_index]['ssid'])
        # Encode SSID into a hex string
        ssid = codecs.encode(ssid.encode('utf-8'), 'hex_codec').decode()

        # Prepare wpa_supplicant configuration with or without WPA enabled
        if (len(password) > 0):
            wpa_supplicant_conf = "network={{\n\tssid={}\n\tpsk=\"{}\"\n}}\n".format(ssid, password)
        else:
            wpa_supplicant_conf = "network={{\n\tssid={}\n\tkey_mgmt=NONE\n\tauth_alg=OPEN\n}}\n".format(ssid)
        # Create /etc/wpa_supplicant/wpa_supplicant.conf
        wpa_supplicant_conf = base64.b64encode(wpa_supplicant_conf.encode()).decode()
        cmdmule_command(
            ser, "echo {} | base64 -d | sudo tee /etc/wpa_supplicant/wpa_supplicant.conf".format(wpa_supplicant_conf))

        # Terminate wpa_supplicant that we used for scanning
        cmdmule_command(ser, "sudo wpa_cli terminate")

        # Decrease dhclient.conf timeout from 60 seconds to 15 seconds
        cmdmule_command(ser, "sudo sed -i 's/#timeout 60;/timeout 15;/' /etc/dhcp/dhclient.conf")

        # Bring up WiFi interface
        print_step("\nConnecting WiFi...")
        cmdmule_command(ser, "sudo ifdown {}".format(wlan_interface))
        cmdmule_command(ser, "sudo ifup {}".format(wlan_interface))

        # Check carrier status
        print_step("\nChecking WiFi connectivity...")
        result = cmdmule_command(ser, "cat /sys/class/net/{}/carrier".format(wlan_interface))
        if result['returncode'] != 0 or int(result['stdout'].strip()) != 1:
            print_error("Error: Failed to associate with WiFi access point.")
            continue
        logger.debug("[connect_wifi] carrier is up")

        # Check IP status
        result = cmdmule_command(ser, "ip addr show {} | grep \"inet \"".format(wlan_interface))
        if result['returncode'] != 0:
            print_error("Error: Failed to get an IP address.")
            continue
        logger.debug("[connect_wifi] interface has ip address")

        break


def task_change_hostname(ser):
    """This task changes the hostname.

    Args:
        ser (Serial): Serial port object

    """
    print_step("\nChanging hostname...")

    # Generate a new bitcoin-computer hostname with a salt
    hostname = "bitcoin-computer-{}".format("".join(random.sample(string.ascii_lowercase + string.digits, 4)))

    # Change the hostname
    result = cmdmule_command(ser, ". /etc/profile.d/hostname.sh && set_hostname {}".format(hostname))
    if result['returncode'] != 0:
        print_error("Error: Failed to change hostname.")
    else:
        print("\n    Hostname: {}".format(hostname))

    # Restart avahi-daemon
    result = cmdmule_command(ser, "sudo systemctl restart avahi-daemon")
    if result['returncode'] != 0:
        print_error("Error: Failed to restart avahi-daemon.")


def task_set_date(ser):
    """This task sets the date.

    Set the date on the BC to the date of the
    host computer.

    Args:
        ser (Serial): Serial port object
    """
    print_step("\nSetting date...")

    result = cmdmule_command(ser, "sudo date -s @{}".format(int(time.time())))
    if result['returncode'] != 0:
        print_error("Error: Failed to set date.")
    else:
        print_step("\nDate successfully set.")


def task_lookup_connection_info(ser):
    """This task looks up the hostname and IP addresses of the target, and
    tests connectivity to the target by SSHing to the target.

    Args:
        ser (Serial): Serial port object

    Returns:
        tuple: Tuple of hostname and a list of IP addresses

    """

    print_step("\nLooking up connection information...")

    # Look up hostname
    result = cmdmule_command(ser, "hostname")
    if result['returncode'] != 0:
        raise Exception("Looking up hostname.")

    hostname = result['stdout'].strip()
    logger.debug("[lookup_connection_info] hostname is %s", hostname)

    addresses = []

    # Look up IPv4 addresses
    ipv4_addresses = cmdmule_command(ser, "ip addr show | grep -o \"inet [0-9\.]*\" | cut -d' ' -f2")
    if ipv4_addresses['returncode'] == 0:
        # Split and filter out 127.0.0.1
        ipv4_addresses = ipv4_addresses['stdout'].strip().split('\n')
        ipv4_addresses = list(filter(lambda ip: ip != "127.0.0.1", ipv4_addresses))
        logger.debug("[lookup_connection_info] ipv4 addresses are %s", str(ipv4_addresses))
        addresses += ipv4_addresses

    # Look up IPv6 addresses
    ipv6_addresses = cmdmule_command(ser, "ip addr show | grep -o \"inet6 [0-9a-f:]*\" | cut -d' ' -f2")
    if ipv6_addresses['returncode'] == 0:
        # Split and filter out ::1
        ipv6_addresses = ipv6_addresses['stdout'].strip().split('\n')
        ipv6_addresses = list(filter(lambda ip: ip != "::1", ipv6_addresses))
        logger.debug("[lookup_connection_info] ipv6 addresses are %s", str(ipv6_addresses))
        addresses += ipv6_addresses

    if len(addresses) == 0:
        raise Exception("No IP addresses found.")

    print("\nConnection Information\n")
    print("    Hostname      {}".format(hostname))
    print("    IP Addresses  {}".format(", ".join(ipv4_addresses + ipv6_addresses)))

    return (hostname, ipv4_addresses, ipv6_addresses)


def task_21_update(ip_address):
    """This task runs 21 update on the target.

    Args:
        ip_address (str): IP address

    """

    print_step("\nRunning 21 update...")
    print_step("Please enter your password when prompted for a password.\n")

    # Run 21 update
    try:
        subprocess.check_call(["ssh", "twenty@" + ip_address, "-q", "-o",
                               "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no", "21", "update"])
    except subprocess.CalledProcessError:
        raise Exception("Running 21 update.")


def task_change_password(ser):
    """This task changes the password for user twenty on the target.

    Args:
        ip_address (str): IP address

    """

    MAX_TRIES = 3
    tries = 0

    while True:

        print_step("\nChanging password for user \"twenty\"...")
        print_step("\nPlease enter a new password for user \"twenty\"")
        print_step("")

        password = getpass.getpass("    New password for user \"twenty\": ")
        verify_password = getpass.getpass("    Repeat new password for user \"twenty\": ")

        if password != verify_password:
            tries += 1
            if tries == MAX_TRIES:
                raise Exception("Changing user password.")
            print_warning("Passwords do not match, please try again.")
            continue
        else:
            break

    if cmdmule_command(ser, "echo 'twenty:{}' | chpasswd".format(password))['returncode'] != 0:
        raise Exception("Failed changing user password.")


def task_cleanup(ser):
    """This task exits cmdmule and the shell session on the target,
    restoring it to the login prompt.

    Args:
        ser (Serial): Serial port object

    """

    # Exit cmdmule program
    ser.writeline("\x03\x03\x03")

    # Exit command line
    ser.writeline("exit")


# Top-level setup routine

def main():
    """Setup a Bitcoin Computer over the serial port."""

    task_assert_host()

    try:
        task_install_serial_driver()
        ser = task_find_serial_port()

        try:
            task_prompt(ser)
            task_login(ser)
            task_cmdmule(ser)
            task_connect_wifi(ser)
            task_change_hostname(ser)
            task_set_date(ser)
            (hostname, ipv4_addresses, ipv6_addresses) = task_lookup_connection_info(ser)
            task_change_password(ser)
            # skip steps that require SSH on Windows
            if not sys.platform.startswith("win"):
                task_21_update(ipv4_addresses[0])
        except KeyboardInterrupt:
            print_error("\nSetup interrupted!")
            sys.exit(1)
        finally:
            task_cleanup(ser)
            ser.close()
    except Exception as e:
        print_error("Error: " + str(e))
        print_error("Double check: have you installed the serial port drivers (Step 2)?")
        print_error("If so, check your USB cable connection and try re-running the script a few times.")
        print_error("(Sometimes it can take a moment for a new device to show up.)")
        print_error("If that doesn't work, please contact support@21.co and we'll help you out.")
        if sys.platform.startswith("win"):
            print_error("\nPress any key to close the window.")
            raw_input()
        sys.exit(1)

    print_step("\nSetup complete!")

    print_step("\nBitcoin Computer configured and online!")
    print_step("")
    print_step("Connection Information\n")
    print_step("    Hostname      {}".format(hostname))
    print_step("    IP Addresses  {}".format(", ".join(ipv4_addresses + ipv6_addresses)))
    print_step("")
    if sys.platform.startswith("win"):
        print_step("Continue setup by connecting to your computer via SSH.")
        print_step("Please refer to the instructions on 21.co/setup")
        print_step("")
        while True:
            quit = raw_input("Type [Y] when you've completed the steps on 21.co/setup.\n").lower()
            if quit in ["y", "yes"]:
                break
    else:
        print_step("You may now disconnect the USB cable from your Bitcoin Computer")
        print_step("and connect over wifi with one of these commands:")
        print_step("")
        print_step("    ssh twenty@{}.local".format(hostname))
        for address in ipv4_addresses:
            print_step("    ssh twenty@{}".format(address))
        print_step("")

if __name__ == "__main__":
    main()
