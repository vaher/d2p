import socket
import fcntl
import struct
import array
import platform

def get_up_ifs_and_ip():
    """
    Used to get a list of the up interfaces and associated IP addresses
    on this machine (linux only).
    Source: http://code.activestate.com/recipes/439093-get-names-of-all-up-network-interfaces-linux-only/

    Returns:
        List of interface tuples.  Each tuple consists of
        (interface name, interface IP)
    """
    SIOCGIFCONF = 0x8912
    MAXBYTES = 8096
    
    arch = platform.architecture()[0]
    if_name_part_len = -1
    if_complete_part_len = -1
    if arch == '32bit':
        if_name_part_len = 20
        if_complete_part_len = 32
    elif arch == '64bit':
        if_name_part_len = 20
        if_complete_part_len = 40
    else:
        raise OSError("Unknown architecture: %s" % arch)
    
    temp_bytecodes = B'\0' * MAXBYTES
    names = array.array('B', temp_bytecodes)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fd = sock.fileno()
    
    op = SIOCGIFCONF
    arg = struct.pack('@iL', MAXBYTES, names.buffer_info()[0])
    struct_temp = fcntl.ioctl(fd, op, arg)
    outbytes = struct.unpack('@iL', struct_temp)[0]
    namestr = names.tostring()
    
    active_interfaces = []
    for i in range(0, outbytes, if_complete_part_len):
        namestr_decoded = namestr[i:i+if_name_part_len].decode("utf-8")
        if_name = namestr_decoded.split('\0', 1)[0]
        if_addr =  socket.inet_ntoa(namestr[i+if_name_part_len:i+24])
        interface = (if_name, if_addr)
        active_interfaces.append(interface)
    sock.close()
    return active_interfaces

    
def print_msg_for_debug(to_sending_msg):
    print(to_sending_msg)
    print("")
    try:
        import android
        droid = android.Android()
        droid.makeToast(to_sending_msg)
    except Exception as e:
        pass
