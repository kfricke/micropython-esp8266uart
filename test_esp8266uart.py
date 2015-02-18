import esp8266uart

esp = esp8266uart.ESP8266(1, 115200)

print('Testing generic methods')
print('=======================')

print('AT startup...')
if esp.test():
    print('Success!')
else:
    print('Failed!')

#print('Soft-Reset...')
#if esp.reset():
#    print('Success!')
#else:
#    print('Failed!')

print('Another AT startup...')
if esp.test():
    print('Success!')
else:
    print('Failed!')

print()

print('Testing WIFI methods')
print('====================')

wifi_mode = 1
print("Testing get_mode/set_mode of value '%s'(%i)..." % (esp8266uart.WIFI_MODES[wifi_mode], wifi_mode))
esp.set_mode(wifi_mode)
if esp.get_mode() == wifi_mode:
    print('Success!')
else:
    print('Failed!')
    
print('Disconnecting from WLAN...')
if esp.disconnect():
    print('Success!')
else:
    print('Failed!')

print('Disconnecting from WLAN again...')
if esp.disconnect():
    print('Success!')
else:
    print('Failed!')

print('Checking if not connected WLAN...')
if esp.get_accesspoint() == None:
    print('Success!')
else:
    print('Failed!')

print('Scanning for WLANs...')
wlans = esp.list_all_accesspoints()
for wlan in wlans:
    print(wlan)
    print("Scanning for WLAN '%s'..." % (wlan['ssid']))
    for wlan2 in esp.list_accesspoints(wlan['ssid']):
        print(wlan2)
    
print('Setting access point mode...')
if esp.set_mode(esp8266uart.WIFI_MODES['Access Point + Station']):
    print('Failed!')
else:
    print('Success!')

