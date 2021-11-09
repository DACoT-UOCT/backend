import re
import pyte
import copy
import datetime
import pandas as pd
import dacot_models as dm
from .config import get_settings
from .telnet_command_executor import TelnetCommandExecutor as TCE
from .graphql_mutations import DEFAULT_VEHICLE_INTERGREEN_VALUE
from .complex_operations import ComputeJunctionPlansTables

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
        self.__re_intergreens_table = re.compile(r'\s(?P<phase_name>[A-Z])\s+(?P<is_demand>[NY])\s+(?P<min_time>\d+)\s+(?P<max_time>\d+)\s+(?P<intergreens>((X|\d+)\s+)+(X|\d+))')
        self.__re_extract_phases = re.compile(r'\s[A-Z]\s\d+')
        self.__re_extract_sequence = re.compile(r'Cyclic Check Sequence\s+:\s\[(?P<sequence>[A-Z]+)')
        self.__re_ctrl_type = re.compile(r'Controller Type\s+:\s\[(?P<ctrl_type>.*)]')
        self.__table_id_to_day = {
            '1': 'LU',
            '2': 'SA',
            '3': 'DO'
        }

    def __step1(self):
        out1 = copy.deepcopy(self.__session1())
        assert list(out1[0].keys()) == list(out1[1].keys())
        progs = self.__build_programs(out1[0])
        plans = self.__build_plans(out1[0])
        return plans, progs

    def __step2(self):
        out2 = copy.deepcopy(self.__session2())
        assert list(out2[0].keys()) == list(out2[1].keys())
        return self.__build_sequence(out2[1])

    def __step3(self):
        out3 = copy.deepcopy(self.__session3())
        assert list(out3[0].keys()) == list(out3[1].keys())
        return self.__build_inters(out3[1])

    def run(self):
        inters = self.__step3()
        seq = self.__step2()
        plans, progs = self.__step1()
        self.__update_project(plans, progs, inters, seq)
        return self.__proj

    def __build_sequence(self, data):
        r = {}
        screen = pyte.Screen(80, 25)
        stream = pyte.Stream(screen)
        for junc in self.__proj.otu.junctions:
            k = 'get-seed-{}'.format(junc.jid)
            for line in self.__posibles_lists_to_list(data[k]):
                stream.feed(line)
            result_screen = '\n'.join(screen.display)
            seq_info = self.__extract_sequence(junc, result_screen)
            known_types = {}
            seq_objs = []
            for s in junc.sequence:
                known_types[s.phid_system] = s.type
            for sid in seq_info['seq']:
                t = 'No Configurada'
                if sid in known_types:
                    t = known_types[sid]
                seq_objs.append(dm.JunctionPhaseSequenceItem(phid_system=sid, phid=str(ord(sid) - 64), type=t))
            r[junc.jid] = {
                'seq': seq_objs,
                'ctype': seq_info['ctype']
            }
        return r

    def __extract_sequence(self, junc, screen):
        r = {}
        print('DEBUG __extract_sequence')
        print('=' * 35)
        print(screen)
        print('=' * 35)
        sequence_match = list(self.__re_extract_sequence.finditer(screen, re.MULTILINE))
        if len(sequence_match) != 1:
            raise ValueError('__extract_sequence: Failed to find Sequence for {}'.format(junc.jid))
        seqstr = sequence_match[0].group('sequence').strip()
        seq = []
        for pid in seqstr:
            seq.append(pid)
        r['seq'] = seq
        ctrl_match = list(self.__re_ctrl_type.finditer(screen, re.MULTILINE))
        if len(ctrl_match) != 1:
            raise ValueError('__extract_sequence: Failed to find ControllerType for {}'.format(junc.jid))
        r['ctype'] = ctrl_match[0].group('ctrl_type').strip()
        return r

    def __build_inters(self, data):
        r = {}
        screen = pyte.Screen(80, 25)
        stream = pyte.Stream(screen)
        for junc in self.__proj.otu.junctions:
            k = 'get-seed-timings-{}'.format(junc.jid)
            for line in self.__posibles_lists_to_list(data[k]):
                stream.feed(line)
            result_screen = '\n'.join(screen.display)
            inters = self.__extract_intergreens(junc, result_screen)
            r[junc.jid] = inters
        return r

    def __extract_intergreens(self, junc, screen):
        print('DEBUG __extract_intergreens')
        print('=' * 35)
        print(screen)
        print('=' * 35)
        rows_match = list(self.__re_intergreens_table.finditer(screen, re.MULTILINE))
        if len(rows_match) == 0:
            raise ValueError('__extract_intergreens: Failed to extract intergreens for {}'.format(junc.jid))
        table = []
        names = []
        for row in rows_match:
            inter_values = row.group('intergreens')
            names.append(row.group('phase_name'))
            trow = [row.group('phase_name'), row.group('is_demand'), row.group('min_time'), row.group('max_time')]
            trow.extend(inter_values.split())
            table.append(trow)
        column_names = ['Phase', 'IsDemand', 'MinTime', 'MaxTime']
        column_names.extend(names)
        for row in table:
            if len(row) != len(column_names):
                raise ValueError('__extract_intergreens: Invalid row length: row={} columns={}'.format(row, len(column_names)))
        df = pd.DataFrame(table, columns=column_names)
        df = df.set_index('Phase')
        cols = df.columns[3:]
        inters = []
        for i in cols:
            for j in cols:
                if i != j and 'X' not in df[i][j]:
                    newi = dm.JunctionIntergreenValue(phfrom=j, phto=i, value=df[i][j])
                    newi.validate()
                    inters.append(newi)
        return inters

    def __update_project(self, plans, progs, inters, seq):
        new_progs = []
        for p in progs:
            i = dm.OTUProgramItem(day=p[0], time=p[1], plan=p[2])
            i.validate()
            new_progs.append(i)
        self.__proj.otu.programs = new_progs
        for junc in self.__proj.otu.junctions:
            junc.intergreens = inters[junc.jid]
            junc.sequence = seq[junc.jid]['seq']
            if junc.metadata.use_default_vi4:
                junc.plans = self.__generate_plans_objs(plans[junc.jid])
                veh_inters = []
                for inter in junc.intergreens:
                    new_inter = dm.JunctionIntergreenValue()
                    new_inter.phfrom = inter.phfrom
                    new_inter.phto = inter.phto
                    new_inter.value = str(DEFAULT_VEHICLE_INTERGREEN_VALUE)
                    veh_inters.append(new_inter)
                junc.veh_intergreens = veh_inters
            else:
                junc.plans = self.__generate_plans_objs(plans[junc.jid])
                veh_inters = []
                inters_map = {}
                for inter in junc.veh_intergreens:
                    if inter.phfrom not in inters_map:
                        inters_map[inter.phfrom] = {}
                    inters_map[inter.phfrom][inter.phto] = str(inter.value)
                for inter in junc.intergreens:
                    new_inter = dm.JunctionIntergreenValue()
                    new_inter.phfrom = inter.phfrom
                    new_inter.phto = inter.phto
                    val = inters_map.get(inter.phfrom, {}).get(inter.phto)
                    if not val:
                        raise ValueError('Missing VI for pair ({}, {})'.format(inter.phfrom, inter.phto))
                    new_inter.value = val
                    veh_inters.append(new_inter)
                junc.veh_intergreens = veh_inters
        compute = ComputeJunctionPlansTables(self.__proj)
        self.__proj.metadata.last_sync_date = datetime.datetime.utcnow()
        self.__proj.metadata.status_date = self.__proj.metadata.last_sync_date
        self.__proj = compute.run()

    def __generate_plans_objs(self, plans):
        res = []
        for p in plans:
            start = []
            for s in p[2]:
                val = dm.JunctionPlanPhaseValue(phid=s[0], value=s[1])
                val.validate()
                start.append(val)
            newp = dm.JunctionPlan(plid=p[0], cycle=p[1], system_start=start)
            newp.validate()
            res.append(newp)
        return res

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
                    res[(self.__table_id_to_day[tid], current_time, prog_match.group('plan'))] = prog_match.group('plan')
                elif is_extra_day[0]:
                    line_without_day = is_extra_day[1]
                    line_day = is_extra_day[2]
                    extra_plan_match = self.__re_program.match(line_without_day)
                    extra_scoot_match = self.__check_is_scoot(line_without_day)
                    extra_demand_match = self.__check_is_demand(line_without_day)
                    if extra_plan_match:
                        res[(line_day, current_time, extra_plan_match.group('plan'))] = extra_plan_match.group('plan')
                    elif extra_scoot_match[0]:
                        res[(line_day, current_time, extra_scoot_match[1])] = extra_scoot_match[1]
                    elif extra_demand_match[0]:
                        res[(line_day, current_time, extra_demand_match[1])] = extra_demand_match[1]
                elif is_scoot_change[0]:
                    res[(self.__table_id_to_day[tid], current_time, is_scoot_change[1])] = is_scoot_change[1]
                elif is_demand_change[0]:
                    res[(self.__table_id_to_day[tid], current_time, is_demand_change[1])] = is_demand_change[1]
                else:
                    pass
        final_progs = []
        for k, v in res.items():
            item = (k[0], k[1], v)
            new_item = (k[0], k[1], k[2], v)
            print('Item: {} -> NewItem: {}'.format(item, new_item))
            final_progs.append(item)
        sorted = self.__sort_programs(final_progs)
        print('Result of __sort_programs: {}'.format(sorted))
        final_result = self.__map_by_time_and_clear(sorted)
        print('Final result of __map_by_time_and_clear: {}'.format(final_result))
        return final_result

    def __map_by_time_and_clear(self, sorted):
        m = {}
        r = []
        for i in sorted:
            k = (i[0], i[1])
            if k not in m:
                m[k] = []
            m[k].append(i[2])
        for k, v in m.items():
            if len(v) > 1:
                if 'XSCO' in v or 'SCOO' in v or 'XDEM' in v or 'DEMA' in v:
                    for x in v:
                        r.append((k[0], k[1], x))
                else:
                    r.append((k[0], k[1], v[-1]))    
            else:
                r.append((k[0], k[1], v[0]))
        return r

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
        sorted_plans = sorted(to_sort, key=lambda x: (x[0], x[1]))
        res = []
        for i in sorted_plans:
            res.append((rdmap[i[0]], i[2], i[3]))
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

    def __session1(self):
        self.__exec.reset()
        self.__control_login()
        for junc in self.__proj.otu.junctions:
            self.__list_plans(junc.jid)
            self.__get_programs(junc.jid)
        self.__logout()
        print('Using plan for {} (__session1): {}'.format(self.__proj.oid, self.__exec.history()))
        self.__exec.run(debug=True)
        out = self.__exec.get_results()
        self.__run_login_check(out)
        return (self.__output_to_text_block(out), out)

    def __session2(self):
        self.__exec.reset()
        self.__control_login()
        for junc in self.__proj.otu.junctions:
            self.__get_sequence(junc.jid)
        self.__logout()
        print('Using plan for {} (__session2): {}'.format(self.__proj.oid, self.__exec.history()))
        self.__exec.run(debug=True)
        out = self.__exec.get_results()
        self.__run_login_check(out)
        return (self.__output_to_text_block(out), out)

    def __session3(self):
        self.__exec.reset()
        self.__control_login()
        for junc in self.__proj.otu.junctions:
            self.__get_inters(junc.jid)
        self.__logout()
        print('Using plan for {} (__session3): {}'.format(self.__proj.oid, self.__exec.history()))
        self.__exec.run(debug=True)
        out = self.__exec.get_results()
        self.__run_login_check(out)
        return (self.__output_to_text_block(out), out)

    def __list_plans(self, jid):
        self.__exec.command('get-plans-{}'.format(jid), 'LIPT {} TIMINGS'.format(jid))
        self.__exec.sleep(self.__read_remote_sleep)
        self.__exec.read_lines(encoding='iso-8859-1', line_ending=b'\x1b8\x1b7')

    def __get_programs(self, jid):
        for day_table_code in range(1, 4):
            self.__exec.command('get-programs-{}-{}'.format(jid, day_table_code), 'OUTT {} {} EXPAND'.format(jid, day_table_code))
            self.__exec.sleep(self.__read_remote_sleep)
            self.__exec.read_lines(encoding='iso-8859-1', line_ending=b'\x1b8\x1b7')

    def __get_sequence(self, jid):
        self.__exec.command('get-seed-{}'.format(jid), 'SEED {}'.format(jid))
        self.__exec.sleep(self.__read_remote_sleep)
        self.__exec.read_until_min_bytes(2000, encoding="iso-8859-1", line_ending=b"\x1b8\x1b7")
        self.__exec.exit_interactive_command()

    def __get_inters(self, jid):
        self.__exec.command('get-seed-timings-{}'.format(jid), 'SEED {} UPPER_TIMINGS'.format(jid))
        self.__exec.sleep(self.__read_remote_sleep)
        self.__exec.read_until_min_bytes(2000, encoding="iso-8859-1", line_ending=b"\x1b8\x1b7")
        self.__exec.exit_interactive_command()

    def __run_login_check(self, out):
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
            for i in self.__posibles_lists_to_list(v):
                clean_line = self.__re_ansi_escape.sub('', i).strip()
                t.append(clean_line)
            r[k] = t
        return r

    def __posibles_lists_to_list(self, v):
        t = []
        for possible_list in v:
            if type(possible_list) == list:
                for line in possible_list:
                    t.append(line)
            else:
                t.append(possible_list)
        return t
