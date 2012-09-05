from .multicastbootstrap import ip_mcast_receiver
from .multicastbootstrap import membermanager

import collections

BootstrapEntry = collections.namedtuple('BootstrapEntry',
                                         ['transportId',
                                          'addr', # IP (or similar) address. None for automatic detection
                                          'port' # Extended information like port
                                         ])

_bootstrap_types = {}
def _registerBootstrap(bootstrapClass):
    _bootstrap_types[bootstrapClass.bootstrap_type] = bootstrapClass
    return bootstrapClass

def create(data):
    return _bootstrap_types[data['bsType']]()


@_registerBootstrap
class MulticastBootstrap(object):
    bootstrap_type = 'local_multicast'
    ui_bootstrap_name = 'Multicast bootstrap'
    
    def start(self, assignedId, io_loop, getAdvertised, onFind):
        """ Start running on the specified io_loop """
        self.assignedId = assignedId
        self._getAdvertised = getAdvertised
        self._onFind = onFind
        self._entries = []
                
        memberManager = membermanager.MemberManager(self._getAdvertised, self.ui_addEntry)
        self._multicastBootstrap = ip_mcast_receiver.MulticastBootstrap(memberManager, io_loop)        

    def start_bootstrap(self):
        self._multicastBootstrap.sending_multicast_start()
        
    def stop_bootstrap(self):
        self._multicastBootstrap.sending_multicast_stop()

    def renotify(self):
        """ Call onFind for all entries this bootstrap has found """
        for e in self._entries:
            self._onFind(e)

    @property
    def ui_entries(self):
        return self._entries

    def ui_addEntry(self, bse):
        print(isinstance(bse, BootstrapEntry))
        #assert isinstance(bse, BootstrapEntry) #TODO: Überlege wie ich es schaffe, dass es die selbe Instanz ist!
        assert bse.addr
        self._entries.append(bse)
        self._onFind(bse)



@_registerBootstrap
class ManualBootstrap(object):
    bootstrap_type = 'manual'
    ui_bootstrap_name = 'Manual bootstrap'

    def start(self, assignedId, io_loop, getAdvertised, onFind):
        """ Start running on the specified io_loop """
        self.assignedId = assignedId
        self._onFind = onFind
        self._entries = []

    def renotify(self):
        """ Call onFind for all entries this bootstrap has found """
        for e in self._entries:
            self._onFind(e)

    @property
    def ui_entries(self):
        return self._entries

    def ui_addEntry(self, bse):
        assert isinstance(bse, BootstrapEntry)
        assert bse.addr
        self._entries.append(bse)
        self._onFind(bse)
