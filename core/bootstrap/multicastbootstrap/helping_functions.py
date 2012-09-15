import socket
import fcntl
import struct
import array
import platform

def get_up_ifs_and_ip():
    """
    Used to get a list of the up interfaces and associated IP addresses
    on this machine (linux only).
    Quelle: http://code.activestate.com/recipes/439093-get-names-of-all-up-network-interfaces-linux-only/

    Returns:
        List of interface tuples.  Each tuple consists of
        (interface name, interface IP)
    """
    SIOCGIFCONF = 0x8912
    MAXBYTES = 8096
    
    arch = platform.architecture()[0]
    var1 = -1
    var2 = -1
    if arch == '32bit':
        var1 = 20
        var2 = 32
    elif arch == '64bit':
        var1 = 16
        var2 = 40
    else:
        raise OSError("Unknown architecture: %s" % arch)
    
    
    
    temp_bytecodes = B'\0' * MAXBYTES
    names = array.array('B', temp_bytecodes)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fd = sock.fileno()
    
    op = SIOCGIFCONF
    arg = struct.pack('iL', MAXBYTES, names.buffer_info()[0])
    struct_temp = fcntl.ioctl(fd, op, arg)
    outbytes = struct.unpack('iL', struct_temp)[0]
    namestr = names.tostring()
    
    active_interfaces = []
    for i in range(0, outbytes, var2):
        namestr_decoded = namestr[i:i+var1].decode("utf-8")
        if_name = namestr_decoded.split('\0', 1)[0]
        if_addr =  socket.inet_ntoa(namestr[i+20:i+24])
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
        #droid.log(to_sending_msg)
    except Exception as e:
        pass
