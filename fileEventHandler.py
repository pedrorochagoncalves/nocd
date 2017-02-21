import pyinotify


class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, noc_pusher):
        self.noc_pusher = noc_pusher

    def process_IN_MODIFY(self, event):
        print "Config file was modified:", event.pathname
        self.noc_pusher.reload_config()