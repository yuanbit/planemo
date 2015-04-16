import click
import os

from planemo.cli import pass_context
from planemo import options


@click.command('shed_lint')
@options.optional_project_arg(exists=True)
@options.optional_tools_arg()
@options.report_level_option()
@options.fail_level_option()
@pass_context
def cli(ctx, path, report_level="all", fail_level="warn"):
    """Check repository for common problems.
    """
    tool_dependencies = os.path.join(path, "tool_dependencies.xml")
    if os.path.exists(tool_dependencies):
        pass
