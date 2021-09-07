import re
from .config import get_settings
from .telnet_command_executor import TelnetCommandExecutor as TCE

class SyncProjectFromControlException(Exception):
    pass

class SyncProject:
    def __init__(self, project):
        self.__proj = project
        self.__exec = TCE(host=get_settings().utc_host, port=get_settings().utc_port)
        self.__read_remote_sleep = 5
        self.__re_ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|[0-9]|\[[0-?]*[ -/]*[@-~])|\r|\n')
        self.__re_program = re.compile(r'(?P<hour>(\d{2}:\d{2}:\d{2})?)(\d{3})?\s+PLAN\s+(?P<junction>[J|A]\d{6})\s+(?P<plan>(\d+|[A-Z]{1,2}))\s+TIMETABLE$')

    def run(self):
        self.__run_login_check()
        out_block = self.__read_control()
        self.__build_programs(out_block)

    def __build_programs(self, out):
        kl = [k for k in out if 'get-programs-' in k]
        for k in kl:
            tid = k[-1]
            for line in out[k]:
                prog_match = self.__re_program.match(line)
                if prog_match:
                    pass
                else:
                    print(line)

    def __read_control(self):
        self.__exec.reset()
        self.__control_login()
        for junc in self.__proj.otu.junctions:
            self.__list_plans(junc.jid)
            self.__get_programs(junc.jid)
        self.__logout()
        print('Using plan for {}: {}'.format(self.__proj.oid, self.__exec.history()))
        self.__exec.run(debug=True)
        out = self.__exec.get_results()
        return self.__output_to_text_block(out)

    def __list_plans(self, jid):
        self.__exec.command('get-plans-{}'.format(jid), 'LIPT {} TIMINGS'.format(jid))
        self.__exec.sleep(self.__read_remote_sleep)
        self.__exec.read_lines(encoding='iso-8859-1', line_ending=b'\x1b8\x1b7')

    def __get_programs(self, jid):
        for day_table_code in range(1, 4):
            self.__exec.command('get-programs-{}-{}'.format(jid, day_table_code), 'OUTT {} {} EXPAND'.format(jid, day_table_code))
            self.__exec.sleep(self.__read_remote_sleep)
            self.__exec.read_lines(encoding='iso-8859-1', line_ending=b'\x1b8\x1b7')

    def __run_login_check(self):
        self.__exec.reset()
        self.__control_login()
        self.__logout()
        print('Using plan for login: {}'.format(self.__exec.history()))
        self.__exec.run(debug=True)
        out = self.__exec.get_results()
        if 'Access Denied' in self.__lines_to_string(out['login-pass']):
            raise SyncProjectFromControlException('Invalid Credentials for Control Server')
        if 'Successfully logged in!' not in self.__lines_to_string(out['login-pass']):
            raise SyncProjectFromControlException('Unknown error in login for Control Servers')

    def __logout(self):
        self.__exec.command('end-session', 'ENDS')

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

    def __output_to_text_block(self, data):
        r = {}
        for k, v in data.items():
            t = []
            for possible_list in v:
                if type(possible_list) == list:
                    for line in possible_list:
                        clean_line = self.__re_ansi_escape.sub('', line).strip()
                        t.append(clean_line)
                else:
                    clean_line = self.__re_ansi_escape.sub('', possible_list).strip()
                    t.append(clean_line)
            r[k] = t
        return r
