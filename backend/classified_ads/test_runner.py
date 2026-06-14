"""Цветной вывод результатов `manage.py test` и подавление шумных логов."""
import sys
import unittest
import warnings

from django.test.runner import DiscoverRunner

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
DIM = '\033[2m'
BOLD = '\033[1m'
RESET = '\033[0m'


def _supports_color() -> bool:
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def _explicit_verbosity_in_argv() -> bool:
    for arg in sys.argv:
        if arg.startswith('--verbosity'):
            return True
        if arg == '-v' or (arg.startswith('-v') and len(arg) == 3 and arg[2].isdigit()):
            return True
    return False


def _colorize(code: str, text: str) -> str:
    if not _supports_color():
        return text
    return f'{code}{text}{RESET}'


class ColoredTextTestResult(unittest.TextTestResult):
    """Результат прогона с цветными метками и именами тестов."""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self._use_color = _supports_color()

    def _c(self, code: str, text: str) -> str:
        if not self._use_color:
            return text
        return f'{code}{text}{RESET}'

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        if self.showAll:
            name = test._testMethodName
            cls = test.__class__.__name__
            doc = test.shortDescription()
            line = f'  {self._c(CYAN, "▶")} {cls}.{name}'
            if doc:
                line += f' {self._c(DIM, "—")} {doc}'
            self.stream.writeln(line)
            self.stream.flush()

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        if self.showAll:
            self.stream.writeln(f'    {self._c(GREEN, "✓ OK")}')
        elif self.dots:
            self.stream.write(self._c(GREEN, '.'))
            self.stream.flush()

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        if self.showAll:
            self.stream.writeln(f'    {self._c(RED, "✗ FAIL")}')
        elif self.dots:
            self.stream.write(self._c(RED, 'F'))
            self.stream.flush()

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        if self.showAll:
            self.stream.writeln(f'    {self._c(RED, "✗ ERROR")}')
        elif self.dots:
            self.stream.write(self._c(RED, 'E'))
            self.stream.flush()

    def addSkip(self, test, reason):
        unittest.TestResult.addSkip(self, test, reason)
        if self.showAll:
            self.stream.writeln(f'    {self._c(YELLOW, "⊘ SKIP")}')
        elif self.dots:
            self.stream.write(self._c(YELLOW, 's'))
            self.stream.flush()


class ColoredDiscoverRunner(DiscoverRunner):
    """DiscoverRunner с цветным выводом (verbosity=2 по умолчанию)."""

    def __init__(self, verbosity=1, **kwargs):
        if not _explicit_verbosity_in_argv():
            verbosity = 2
        super().__init__(verbosity=verbosity, **kwargs)

    def get_resultclass(self):
        return ColoredTextTestResult

    def run_suite(self, suite, **kwargs):
        result = super().run_suite(suite, **kwargs)
        self._last_result = result
        return result

    def run_tests(self, test_labels, **kwargs):
        warnings.filterwarnings(
            'ignore',
            message='Pagination may yield inconsistent results',
            category=UserWarning,
            module='rest_framework.pagination',
        )
        failures = super().run_tests(test_labels, **kwargs)
        if getattr(self, '_last_result', None) is not None:
            self._print_summary(self._last_result)
        return failures

    def suite_result(self, suite, result, **kwargs):
        return super().suite_result(suite, result, **kwargs)

    def _print_summary(self, result) -> None:
        total = result.testsRun
        failed = len(result.failures) + len(result.errors)
        skipped = len(result.skipped)
        passed = total - failed - skipped

        if failed:
            status = _colorize(f'{RED}{BOLD}', 'FAILED')
        else:
            status = _colorize(f'{GREEN}{BOLD}', 'OK')

        main_line = (
            f'{_colorize(BOLD, "Итого:")} {status} — '
            f'{_colorize(GREEN, str(passed))} из {total} тестов прошли успешно'
        )
        if failed:
            main_line += f', {_colorize(RED, str(failed))} с ошибками'
        if skipped:
            main_line += f', {_colorize(YELLOW, str(skipped))} пропущено'

        sys.stdout.write(f'\n{main_line}\n')
        sys.stdout.flush()
