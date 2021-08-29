import unittest
from dacot_parser.telnet_command_executor import TelnetCommandExecutor


class TestTelnetExecutorInternet(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestTelnetExecutorInternet, self).__init__(*args, **kwargs)
        self.executor = TelnetCommandExecutor("telehack.com")

    def test_cowsay_session(self):
        self.skipTest("Ignored")
        self.executor.reset()
        self.executor.read_lines()
        self.executor.command("cowsay", "cowsay Works!")
        self.executor.read_until(">", 2)
        self.executor.read_lines()
        self.executor.command("exit", "exit")
        self.executor.run()
        results = self.executor.get_results()
        self.assertIn("starwars", results["init"][0][19])
        self.assertIn("cowsay Works!\r\n", results["cowsay"][0])
        self.assertIn("< Works! >", results["cowsay"][0])
        self.assertEqual(">", results["cowsay"][0][-1])

    def test_start_and_exit_session(self):
        self.skipTest("Ignored")
        self.executor.reset()
        self.executor.command("end-session", "exit")
        self.executor.run()
