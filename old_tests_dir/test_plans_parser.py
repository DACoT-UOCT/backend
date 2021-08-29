import os
import unittest
from dacot_parser.utc_plan_parser import UTCPlanParser


class TestPlanParser(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPlanParser, self).__init__(*args, **kwargs)
        self.parser = UTCPlanParser()
        self.input = os.path.join(os.path.dirname(__file__), "plans.txt")

    def test_parse_file(self):
        plans = self.parser.parse_plans_file(self.input)
        self.assertEqual(len(plans.keys()), 4)
        self.assertEqual(plans["J175551"][3]["cycle"], 100)
        self.assertEqual(plans["J175551"][3]["system_start"]["1"], 41)
        self.assertEqual(plans["J175551"][3]["system_start"]["124"], 11)
        self.assertEqual(plans["J175561"][3]["system_start"]["12!"], 38)

    def test_parse_invalid_plan(self):
        self.assertFalse(
            self.parser.parse_plan("Mo 09:54:04 22-JUN-20 Current plan Timings")[0]
        )
        self.assertFalse(
            self.parser.parse_plan(
                "Plan   1 J001 PROVIDENCIA-MIGUEL.CLARO________ CY096 B 42, A 67"
            )[0]
        )
        self.assertFalse(
            self.parser.parse_plan(
                "Plan   J00111 PROVIDENCIA-MIGUEL.CLARO________ CY096 B 42, A 67"
            )[0]
        )

    def test_parse_invalid_phases(self):
        self.assertFalse(
            self.parser.parse_plan(
                "Plan   1 J001121 M.MONTT-PROVIDE CY104 C, A 46, B 97"
            )[0]
        )
        self.assertFalse(
            self.parser.parse_plan(
                "Plan   1 J001121 M.MONTT-PROVIDE CY104 C 30, A 46 B 97"
            )[0]
        )
        self.assertFalse(
            self.parser.parse_plan(
                "Plan   1 J001121 M.MONTT-PROVIDE CY104 C 30 A? 46, B 97"
            )[0]
        )
        self.assertFalse(
            self.parser.parse_plan(
                "Plan   1 J001121 M.MONTT-PROVIDE CY104 C 30, A 46, 97"
            )[0]
        )
