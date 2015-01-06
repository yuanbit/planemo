from __future__ import print_function
import os

import shutil
import tempfile
import traceback

import click

from planemo import options
from planemo.cli import pass_context
from planemo import shed2tap
from planemo import shed

TOOLSHED_MAP = {
    "toolshed": "https://toolshed.g2.bx.psu.edu",
    "testtoolshed": "https://testtoolshed.g2.bx.psu.edu",
}


@click.command('shed_dependencies')
@options.brew_option()
@click.argument(
    'dependencies_xml',
    default="./tool_dependencies.xml",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ))
@click.option('--git_tap_username', default="jmchilton")
@options.shed_target_option()
@options.shed_owner_option()
@options.shed_name_option()
@pass_context
def cli(ctx, dependencies_xml, brew=None, **kwds):
    """Attempt to convert Tool Shed tool_dependencies.xml into a platform
    Homebrew recipe and install.
    """
    tool_shed = kwds["shed_target"]
    owner, name = shed.repo_name_and_owner(ctx, dependencies_xml, **kwds)
    repo_dict = {"owner": owner, "name": name}
    tap = shed2tap.Tap("%s/%s" % (kwds["git_tap_username"], tool_shed))
    repo = shed2tap.Repo.from_api(tool_shed, repo_dict)
    work_dir = tempfile.mkdtemp()
    try:
        dependencies = shed2tap.Dependencies(
            dependencies_xml,
            repo,
            tap
        )
        for package in dependencies.packages:
            try:
                (file_name, contents) = package.to_recipe()
                recipe_path = os.path.join(work_dir, file_name)
                open(recipe_path, "w").write(contents)
                print(recipe_path)
            except Exception as e:
                traceback.print_exc()
                message = "Failed to convert package [%s], exception [%s]"
                print(message % (package, e))
    finally:
        shutil.rmtree(work_dir)
