from .config import get_settings
from .telnet_command_executor import TelnetCommandExecutor as TCE

class SyncProjectFromControlException(Exception):
    pass

class SyncProject:
    def __init__(self, project):
        self.__proj = project
        self.__exec = TCE(host=get_settings().utc_host, port=get_settings().utc_port)

    def run(self):
        self.__run_login_check()
        for junc in self.__proj.otu.junctions:
            print('Starting Sync for {}'.format(junc.jid))

    def __run_login_check(self):
        self.__exec.reset()
        self.__control_login()
        print('Using plan for login: {}'.format(self.__exec.history()))
        self.__exec.run(debug=True)
        out = self.__exec.get_results()
        if 'Access Denied' in self.__lines_to_string(out['login-pass']):
            raise SyncProjectFromControlException('Invalid Credentials for Control Server')

    def __lines_to_string(self, l):
        return ''.join(self.__flatten(l))

    def __flatten(self, l):
        return [i for s in l for i in s]

    def __control_login(self):
        self.__exec.read_until('Username:', 15)
        self.__exec.command('login-user', get_settings().utc_user)
        self.__exec.read_until('Password:', 15)
        self.__exec.command('login-pass', get_settings().utc_passwd)
        self.__exec.read_lines(encoding='iso-8859-1')
