from pyb import UART
from pyb import delay
from pyb import micros, elapsed_micros

uart = UART(1, 115200)

CMDS_GENERIC = {
    'TEST_AT': b'AT',
    'RESET': b'AT+RST',
    'VERSION_INFO': b'AT+GMR',
    'DEEP_SLEEP': b'AT+GSLP',
    'ECHO': b'ATE',
    'FACTORY_RESET': b'AT+RESTORE',
    'UART_CONFIG': b'AT+UART'
    }

CMDS_WIFI = {
    'MODE' : b'AT+CWMODE',
    'CONNECT': b'AT+CWJAP',
    'LIST_APS': b'AT+CWLAP',
    'DISCONNECT': b'AT+CWQAP',
    'AP_SET_PARAMS': b'AT+CWSAP',
    'AP_LIST_CLIENTS': b'AT+CWLIF',
    'AP_DHCP': b'AT+CWDHCP',
    'AUTO_CONNECT': b'AT+CWAUTOCONN',
    'SET_STATION_MAC': b'AT+CIPSTAMAC',
    'SET_AP_MAC': b'AT+CIPAPMAC',
    'SET_STATION_IP': b'AT+CIPSTA',
    'SET_AP_IP': b'AT+CIPAP'
    }

CMDS_IP = {
    'STATUS': b'AT+CIPSTATUS',
    'START': b'AT+CIPSTART',
    'SEND': b'AT+CIPSEND',
    'CLOSE': b'AT+CIPCLOSE',
    'GET_LOCAL_IP': b'AT+CIFSR',
    'SET_MUX_MODE': b'AT+CIPMUX',
    'CONFIG_SERVER': b'AT+CIPSERVER',
    'SET_TX_MODE': b'AT+CIPMODE',
    'SET_TCP_SERVER_TIMEOUT': b'AT+CIPSTO',
    'UPGRADE': b'AT+CIUPDATE',
    'PING': b'AT+PING'
    }
    
WIFI_MODES = {
    1: 'Station',
    2: 'Access Point',
    3: 'Access Point + Station'
    }
    
WIFI_ENCRYPTION_PROTOCOLS = {
    0: 'OPEN',
    1: 'WEP',
    2: 'WPA_PSK',
    3: 'WPA2_PSK',
    4: 'WPA_WPA2_PSK'
    }

class CommandError(Exception):
    pass
    
class CommandFailure(Exception):
    pass
    
class UnknownWIFIModeError(Exception):
    pass
    
def sendcommand(cmd, timeout=0, debug=False):
    """Send a command to the ESP8266 module over UART and return the 
    output.
    After sending the command there is a 1 second timeout while waiting 
    for an anser on UART. For long running commands (like AP scans) there 
    is an additional 3 seconds grace period to return results over UART.
    Raises an CommandError if an error occurs and an CommandFailure if a 
    command fails to execute."""
    if debug:
        start = micros()
    output = []
    okay = False
    if cmd == '' or cmd == b'':
        raise CommandError("Unknown command '" + cmd + "'!")
    # AT commands must be finalized with an '\r\n'
    cmd += '\r\n'
    if debug:
        print("%8i - TX: %s" % (elapsed_micros(start), str(cmd)))
    uart.write(cmd)
    # wait at maximum one second for a command reaction
    cmd_timeout = 100
    while cmd_timeout > 0:
        if uart.any():
            output.append(uart.readline())
            if debug:
                print("%8i - RX: %s" % (elapsed_micros(start), str(output[-1])))
            if output[-1].rstrip() == b'OK':
                if debug:
                    print("%8i - 'OK' received!" % (elapsed_micros(start)))
                okay = True
            delay(10)
        cmd_timeout -= 1
    if cmd_timeout == 0 and len(output) == 0:
        print("%8i - RX timeout of answer after sending AT command!" % (elapsed_micros(start)))
    # read output if present
    while uart.any():
        output.append(uart.readline())
        if debug:
            print("%8i - RX: %s" % (elapsed_micros(start), str(output[-1])))
        if output[-1].rstrip() == b'OK':
            if debug:
                print("%8i - 'OK' received!" % (elapsed_micros(start)))
            okay = True
    # handle output of AT command 
    if len(output > 0):
        if output[-1].rstrip() == b'ERROR':
            raise CommandError('Command error!')
        elif output[-1].rstrip() == b'OK':
            okay = True
        elif not okay:
            # some long running commands do not return OK in case of success 
            # and/or take some time to yield all output.
            if timeout == 0:
                cmd_timeout = 300
            else:
                if debug:
                    print("%8i - Using RX timeout of %i ms" % (elapsed_micros(start), timeout))
                cmd_timeout = timeout / 10
            while cmd_timeout > 0:
                delay(10)
                if uart.any():
                    output.append(uart.readline())
                    if debug:
                        print("%8i - RX: %s" % (elapsed_micros(start), str(output[-1])))
                    if output[-1].rstrip() == b'OK':
                        okay = True
                        break
                    elif output[-1].rstrip() == b'FAIL':
                        raise CommandFailure()
                cmd_timeout -= 1
        if not okay and cmd_timeout == 0 and debug:
            print("%8i - RX-Timeout occured and no 'OK' received!" % (elapsed_micros(start)))
    return output
    
def joinargs(*args):
    """Joins all given arguments as the ESP8266 needs them for the argument 
    string in a 'set' type command.
    Strings must be quoted using '"' and no spaces outside of quoted 
    srrings are allowed."""
    if len(args) == 1 and type(args) == tuple:
        args = args[0]
    str_args = []
    for arg in args:
        if type(arg) is str:
            str_args.append(b'"' + arg + b'"')
        else:
            str_args.append(b'' + str(arg))
    return b','.join(str_args)
    
def parseaccesspointstr(ap_str):
    """Parse an accesspoint string description into a hashmap containing 
    its parameters. Returns None if string could not be split into 5 
    fields."""
    ap_params = ap_str.split(b',')
    if len(ap_params) == 5:
        (enc_mode, ssid, rssi, mac, channel) = ap_params
        ap = {
            'encryption_protocol': int(enc_mode), 
            'ssid': ssid, 
            'rssi': int(rssi), 
            'mac': mac, 
            'channel': int(channel)
            }
    else:
        ap = None
    return ap
    
def querycommand(cmd, timeout=0, debug=False):
    """Sends a 'query' type command and return the relevant output line, 
    containing the queried parameter."""
    return sendcommand(cmd + b'?', timeout=timeout, debug=debug)[1].rstrip()
        
def setcommand(cmd, *args, timeout=0, debug=False):
    """Send a 'set' type command and return all lines of the output which 
    are not command echo and status codes."""
    args_str = joinargs(args)
    print(args_str)
    return sendcommand(cmd + b'=' + args_str, timeout=timeout, debug=debug)[1:-2]
    
def executecommand(cmd, timeout=0, debug=False):
    """Send an 'execute' type command and return all lines of the output 
    which are not command echo and status codes."""
    return sendcommand(cmd, timeout=timeout, debug=debug)[1:-2]

def test():
    """Test the AT command interface."""
    executecommand(CMDS_GENERIC['TEST_AT'], debug=True)
    
def reset(debug=True):
    """Reset the module and read the boot message.
    ToDo: Interpret the boot message and do something reasonable with it, 
    if possible."""
    if debug:
        start = micros()
    executecommand(CMDS_GENERIC['RESET'], debug=True)
    # wait for module to boot and messages appearing on uart
    timeout = 300
    while not uart.any() and timeout > 0:
        delay(10)
        timeout -= 1
    if debug and timeout == 0:
        print("%8i - RX timeout occured!" % (elapsed_micros(start)))
    # wait for messages to finish
    timeout = 300
    while timeout > 0:
        if uart.any():
            line = uart.readline()
            if debug:
                print("%8i - RX: %s" % (elapsed_micros(start), str(line)))
        delay(20)
        timeout -= 1
    if debug and timeout == 0:
        print("%8i - RTimeout occured while waiting for module to boot!" % (elapsed_micros(start)))
    
class WIFI():
    """Combines all WIF methods of this API."""
    
    def getmode():
        """Returns the mode the ESP WIFI is in:
            1: station mode
            2: accesspoint mode
            3: accesspoint and station mode
        Check the hashmap espuart.WIFI_MODES for a name lookup. 
        Raises an UnknownWIFIModeError if the mode was not a valid or 
        unknown.
        """
        mode = int(querycommand(CMDS_WIFI['MODE']).split(b':')[1])
        if mode in WIFI_MODES.keys():
            return mode
        else:
            raise UnknownWIFIModeError("Mode '%s' not known!" % mode)
            
    def setmode(mode):
        """Set the given WIFI mode.
        Raises UnknownWIFIModeError in case of unknown mode."""
        if mode not in WIFI_MODES.keys():
            raise UnknownWIFIModeError("Mode '%s' not known!" % mode)
        setcommand(CMDS_WIFI['MODE'], mode)
    
    def getaccesspoint():
        """Read the SSID of the currently joined access point.
        The SSID 'No AP' tells us that we are not connected to an access 
        point!"""
        answer = querycommand(CMDS_WIFI["CONNECT"])
        #print("Answer: " + str(answer))
        if answer == b'No AP':
            result = None
        else:
            result = answer.split(b'+' + CMDS_WIFI['CONNECT'][3:] + b':')[1][1:-1]
        return result
        
    def connect(ssid, psk):
        """Tries to connect to a WIFI network using the given SSID and 
        pre shared key (PSK). Uses a 20 second timeout for the connect 
        command."""
        setcommand(CMDS_WIFI['CONNECT'], ssid, psk, debug=True, timeout=20000)
    
    def disconnect():
        """Tries to connect to a WIFI network using the given SSID and 
        pre shared key (PSK)."""
        executecommand(CMDS_WIFI['DISCONNECT'])
        
    def listallaccesspoints():
        """List all available access points.
        TODO: The IoT AT firmware 0.9.5 seems to sporadically yield 
        rubbish or mangled AP-strings. Check needed!"""
        aps = []
        answer = executecommand(CMDS_WIFI['LIST_APS'])
        for ap in answer:
            ap_str = ap.rstrip().split(b'+' + CMDS_WIFI['LIST_APS'][3:] + b':')[1][1:-1]
            # parsing the ap_str may not work because of rubbish strings 
            # returned from the AT command. None is returned in this case.
            ap = paresaccesspointstr(ap_str)
            if ap:
                aps.append(ap)
        return aps
        
    def listaccesspoints(*args):
        """List accesspoint matching the parameters given by the 
        argument list.
        The arguments may be of the types string or integer. Strings can 
        describe MAC adddresses or SSIDs while the integers refer to 
        channel names."""
        return setcommand(CMDS_WIFI['LIST_APS'], args, debug=True)
        
    def setaccesspointconfig(ssid, password, channel, encrypt_proto):
        """Configure the parameters for the accesspoint mode. The module 
        must be in access point mode for this to work.
        After setting the parameters the module is reset to 
        activate them.
        The password must be at least 8 characters long up to a maximum of 
        64 characters.
        Raises CommandFailure in case the WIFI mode is not set to mode 2 
        (access point) or 3 (access point and station) or the WIFI 
        parameters are not valid."""
        if WIFI.getmode() not in (2, 3):
            raise CommandFailure('WIFI not set to an access point mode!')
        if type(ssid) is not str:
            raise CommandFailure('SSID must be of type str!')
        if type(password) is not str:
            raise CommandFailure('Password must be of type str!')
        if len(password) > 64 or len(password) < 8:
            raise CommandFailure('Wrong password length (8..64)!')
        if channel not in range(1, 15) and type(channel) is not int:
            raise CommandFailure('Invalid WIFI channel!')
        if encrypt_proto not in (0, 2, 3, 4) and type(encrypt_proto) is not int:
            raise CommandFailure('Invalid encryption protocol!')
        setcommand(CMDS_WIFI['AP_SET_PARAMS'], ssid, password, channel, encrypt_proto, debug=True)
        reset()
        
    def getaccesspointconfig():
        """Reads the current access point configuration. The module must 
        be in an acces point mode to work.
        Returns a hashmap containing the access point parameters.
        Raises CommandFailure in case of wrong WIFI mode set."""
        if WIFI.getmode() not in (2, 3):
            raise CommandFailure('WIFI not set to an access point mode!')
        (ssid, password, channel, encryption_protocol) = querycommand(CMDS_WIFI['AP_SET_PARAMS'], debug=True).split(b':')[1].split(b',')
        return {
            'ssid': ssid,
            'password': password,
            'channel': int(channel),
            'encryption_protocol': int(encryption_protocol)
            }
            
class IP():
    """This class maps the TCP/IP and UDP/IP based commands."""
    
    def getconnectionstatus():
        """Get connection information."""
        return executecommand(CMDS_IP['STATUS'])
        
    def startconnection(protocol, dest_ip, dest_port):
        """Start a TCP or UDP connection. 
        ToDo: Implement MUX mode. Currently only single connection mode is
        supported!"""
        setcommand(CMDS_IP['START'], protocol, dest_ip, dest_port, debug=True)
        
    def send(data):
        """Send data over the current connection."""
        setcommand(CMDS_IP['SEND'], len(data), debug=True)
        print(b'>' + data)
        uart.write(data)
        
    def ping(destination):
        """Ping the destination address or hostname."""
        return setcommand(CMDS_IP['PING'], destination)