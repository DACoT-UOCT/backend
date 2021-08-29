import os
import unittest
from dacot_parser.utc_program_parser import UTCProgramParser


class TestProgramParser(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestProgramParser, self).__init__(*args, **kwargs)
        self.parser = UTCProgramParser()
        self.input = os.path.join(os.path.dirname(__file__), "programs.txt")

    def test_parse_program(self):
        programs = self.parser.parse_program_file(self.input, "S")
        self.assertEqual(len(programs.keys()), 7)
        self.assertEqual(programs["J099181"]["S"][0], ["01:00:02", "31"])
        self.assertEqual(programs["J099181"]["S"][0][0], "01:00:02")
        self.assertEqual(programs["J099181"]["S"][1][1], "XS")

    def test_parse_invalid_program(self):
        self.assertFalse(
            self.parser.parse_program(
                "00:01:00   ACAS 321 (-00:01 INICIALIZA SPECIAL FACLTY, SABADO)"
            )[0]
        )
        self.assertFalse(self.parser.parse_program("002   PLAN J0991 S TIMETABLE")[0])
