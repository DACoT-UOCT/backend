import re
import dacot_models as dm
from .config import get_settings
from .telnet_command_executor import TelnetCommandExecutor as TCE

class SyncProjectFromControlException(Exception):
    pass

class SyncProject:
    def __init__(self, project):
        self.__proj = project
        self.__exec = TCE(host=get_settings().utc_host, port=get_settings().utc_port)
        self.__read_remote_sleep = 3
        self.__read_remote_login_sleep = 12
        self.__re_ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|[0-9]|\[[0-?]*[ -/]*[@-~])|\r|\n')
        self.__re_program = re.compile(r'(?P<hour>(\d{2}:\d{2}:\d{2})?)(\d{3})?\s+PLAN\s+(?P<junction>[J|A]\d{6})\s+(?P<plan>(\d+|[A-Z]{1,2}))\s+TIMETABLE$')
        self.__re_scoot = re.compile(r'^(\d+)\s*(XSCO|SCOO).*$')
        self.__re_demand = re.compile(r'^(\d+)\s*(XDEM|DEMA).*$')
        self.__re_program_hour = re.compile(r'(?P<hour>\d{2}:\d{2}:\d{2}).*$')
        self.__re_plan = re.compile(r'^Plan\s+(?P<id>\d+)\s(?P<junction>J\d{6}).*(?P<cycle>CY\d{3})\s(?P<phases>[A-Z0-9\s,!*]+)$')
        self.__re_extract_phases = re.compile(r'\s[A-Z]\s\d+')
        self.__table_id_to_day = {
            '1': 'LU',
            '2': 'SA',
            '3': 'DO'
        }

    def run(self):
        self.__run_login_check()
        out_block = self.__read_control()
        progs = self.__build_programs(out_block)
        plans = self.__build_plans(out_block)
        self.__update_project(plans, progs)
        return self.__proj

    def __update_project(self, plans, progs):
        new_progs = []
        for p in progs:
            i = dm.OTUProgramItem(day=p[0], time=p[1], plan=p[2])
            i.validate()
            new_progs.append(i)
        self.__proj.otu.programs = new_progs
        # Update plans
        # Call SetVehInt, if use_default_int check
        # Call ComputeTables

    def __build_plans(self, out):
        res = {}
        for junc in self.__proj.otu.junctions:
            k = 'get-plans-{}'.format(junc.jid)
            res[junc.jid] = []
            for line in out[k]:
                match = self.__re_plan.match(line)
                if match:
                    plan_id = match.group('id')
                    cycle = match.group('cycle')
                    cycle_int = int(cycle.split('CY')[1])
                    phases = []
                    for x in self.__re_extract_phases.findall(' {}'.format(match.group('phases'))):
                        name, start = x.strip().split()
                        phases.append((str(ord(name) - 64), str(int(start))))
                    res[junc.jid].append((plan_id, cycle_int, phases))
        return res

    def __build_programs(self, out):
        kl = [k for k in out if 'get-programs-' in k]
        res = {}
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
                    res[(self.__table_id_to_day[tid], current_time)] = prog_match.group('plan')
                elif is_extra_day[0]:
                    line_without_day = is_extra_day[1]
                    line_day = is_extra_day[2]
                    extra_plan_match = self.__re_program.match(line_without_day)
                    extra_scoot_match = self.__check_is_scoot(line_without_day)
                    extra_demand_match = self.__check_is_demand(line_without_day)
                    if extra_plan_match:
                        res[(line_day, current_time)] = extra_plan_match.group('plan')
                    elif extra_scoot_match[0]:
                        res[(line_day, current_time)] = extra_scoot_match[1]
                    elif extra_demand_match[0]:
                        res[(line_day, current_time)] = extra_demand_match[1]
                elif is_scoot_change[0]:
                    res[(self.__table_id_to_day[tid], current_time)] = is_scoot_change[1]
                elif is_demand_change[0]:
                    res[(self.__table_id_to_day[tid], current_time)] = is_demand_change[1]
                else:
                    pass
        final_progs = []
        for k, v in res.items():
            final_progs.append((k[0], k[1], v))
        return self.__sort_programs(final_progs)

    def __sort_programs(self, progs):
        dmap = {
            'LU': 0,
            'MA': 1,
            'MI': 2,
            'JU': 3,
            'VI': 4,
            'SA': 5,
            'DO': 6
        }
        rdmap = {
            0: 'LU',
            1: 'MA',
            2: 'MI',
            3: 'JU',
            4: 'VI',
            5: 'SA',
            6: 'DO'
        }
        to_sort = []
        for p in progs:
            a = dmap[p[0]]
            b = self.__time_to_mins(p[1])
            to_sort.append((a, b, p[1], p[2]))
        print(to_sort)
        sorted_plans = sorted(to_sort, key=lambda x: (x[0], x[1]))
        res = []
        for i in sorted_plans:
            res.append((rdmap[i[0]], i[2], i[3]))
        print(res)
        return res

    def __time_to_mins(self, timestr):
        h, m = timestr.split(':')
        return int(h) * 60 + int(m)

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
            'MONDAY ': 'LU',
            'TUESDAY ': 'MA',
            'WEDNESDAY ': 'MI',
            'THURSDAY ': 'JU',
            'FRIDAY ': 'VI',
            'SATURDAY ': 'SA',
            'SUNDAY ': 'DO'
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
            raise SyncProjectFromControlException('Unknown error in login for Control Server')

    def __logout(self):
        self.__exec.command('end-session', 'ENDS')

    def __lines_to_string(self, l):
        return ''.join(self.__flatten(l))

    def __flatten(self, l):
        return [i for s in l for i in s]

    def __control_login(self):
        self.__exec.read_until('Username:', self.__read_remote_login_sleep)
        self.__exec.command('login-user', get_settings().utc_user)
        self.__exec.read_until('Password:', self.__read_remote_login_sleep)
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
