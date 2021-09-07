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
        self.__re_scoot = re.compile(r'^(\d+)\s*(XSCO|SCOO).*$')
        self.__re_demand = re.compile(r'^(\d+)\s*(XDEM|DEMA).*$')
        self.__re_program_hour = re.compile(r'(?P<hour>\d{2}:\d{2}:\d{2}).*$')

    def run(self):
        self.__run_login_check()
        out_block = self.__read_control()
        self.__build_programs(out_block)

    def __build_programs(self, out):
        kl = [k for k in out if 'get-programs-' in k]
        for k in kl:
            tid = k[-1]
            current_time = ''
            for line in out[k]:
                new_hour = self.__check_new_hour(line)
                prog_match = self.__re_program.match(line)
                is_extra_day = self.__check_is_day(line)
                is_scoot_change = self.__check_is_scoot(line)
                is_demand_change = self.__check_is_demand(line)
                if new_hour[0]:
                    current_time = new_hour[1]
                if prog_match:
                    pass
                elif is_extra_day[0]:
                    line_without_day = is_extra_day[1]
                    line_table = is_extra_day[2]
                    pass
                elif is_scoot_change[0]:
                    pass
                elif is_demand_change[0]:
                    pass
                else:
                    pass

    def __check_new_hour(self, line):
        match = self.__re_program_hour.match(line)
        if match:
            return (True, match.group('hour')[:-3])
        return (False, None)

    def __check_is_demand(self, line):
        if self.__re_demand.match(line):
            if 'XDEM' in line:
                return (True, 'XDEM')
            elif 'DEMA' in line:
                return (True, 'DEMA')
            else:
                return (False, None)
        else:
            return (False, None)

    def __check_is_scoot(self, line):
        if self.__re_scoot.match(line):
            if 'XSCO' in line:
                return (True, 'XSCO')
            elif 'SCOO' in line:
                return (True, 'SCOO')
            else:
                return (False, None)
        else:
            return (False, None)

    def __check_is_day(self, line):
        to_spanish = {
            'MONDAY ': 'L',
            'TUESDAY ': 'MA',
            'WEDNESDAY ': 'MI',
            'THURSDAY ': 'J',
            'FRIDAY ': 'V',
            'SATURDAY ': 'S',
            'SUNDAY ': 'D'
        }
        days = ['MONDAY ', 'TUESDAY ', 'WEDNESDAY ', 'THURSDAY ', 'FRIDAY ', 'SATURDAY ', 'SUNDAY ']
        for d in days:
            if d in line:
                return (True, line.replace(d, ''), to_spanish[d])
        return (False, None, None)

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
