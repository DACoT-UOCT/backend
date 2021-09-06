
class SyncProject:
    def __init__(self, project):
        self.__proj = project

    def run(self):
    	for junc in self.__proj.otu.junctions:
    		print('Starting Sync for {}'.format(junc.jid))
