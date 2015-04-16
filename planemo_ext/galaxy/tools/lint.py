from __future__ import print_function
import inspect
from galaxy.util import submodules

LEVEL_ALL = "all"
LEVEL_WARN = "warn"
LEVEL_ERROR = "error"


def lint_xml(tool_xml, use_schema=False, level=LEVEL_ALL, fail_level=LEVEL_WARN):
    import galaxy.tools.linters
    lint_context = LintContext(level=level, use_schema=use_schema)
    linter_modules = submodules.submodules(galaxy.tools.linters)
    for module in linter_modules:
        for (name, value) in inspect.getmembers(module):
            if callable(value) and name.startswith("lint_"):
                try:
                    lint_context.lint(module, name, value, tool_xml)
                except SkipLint:
                    pass
    return lint_context.failed(fail_level)


class LintContext(object):

    def __init__(self, level, use_schema):
        self.level = level
        self.found_errors = False
        self.found_warns = False
        self.use_schema = use_schema

    def lint(self, module, name, lint_func, tool_xml):
        name = name.replace("tsts", "tests")
        self.printed_linter_info = False
        self.valid_messages = []
        self.info_messages = []
        self.warn_messages = []
        self.error_messages = []
        lint_func(tool_xml, self)
        # TODO: colorful emoji if in click CLI.
        if self.error_messages:
            status = "FAIL"
        elif self.warn_messages:

            status = "WARNING"
        else:
            status = "CHECK"

        def print_linter_info():
            if self.printed_linter_info:
                return
            self.printed_linter_info = True
            print("Applying linter %s... %s" % (name, status))

        for message in self.error_messages:
            self.found_errors = True
            print_linter_info()
            print(".. ERROR: %s" % message)

        if self.level != LEVEL_ERROR:
            for message in self.warn_messages:
                self.found_warns = True
                print_linter_info()
                print(".. WARNING: %s" % message)

        if self.level == LEVEL_ALL:
            for message in self.info_messages:
                print_linter_info()
                print(".. INFO: %s" % message)
            for message in self.valid_messages:
                print_linter_info()
                print(".. CHECK: %s" % message)

    def __handle_message(self, message_list, message, *args):
        if args:
            message = message % args
        message_list.append(message)

    def valid(self, message, *args):
        self.__handle_message(self.valid_messages, message, *args)

    def info(self, message, *args):
        self.__handle_message(self.info_messages, message, *args)

    def error(self, message, *args):
        self.__handle_message(self.error_messages, message, *args)

    def warn(self, message, *args):
        self.__handle_message(self.warn_messages, message, *args)

    def failed(self, fail_level):
        found_warns = self.found_warns
        found_errors = self.found_errors
        if fail_level == LEVEL_WARN:
            lint_fail = (found_warns or found_errors)
        else:
            lint_fail = found_errors
        return not lint_fail


class SkipLint(Exception):
    pass
