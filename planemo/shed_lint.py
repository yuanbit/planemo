import os
from galaxy.tools.lint import LintContext


def lint_repository(path, report_level, fail_level):
    lint_context = LintContext(report_level)
    tool_dependencies = os.path.join(path, "tool_dependencies.xml")
    if os.path.exists(tool_dependencies):
        pass
