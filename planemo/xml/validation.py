import abc
from collections import namedtuple
import subprocess

from galaxy.tools.deps.commands import which
from planemo.io import (
    info,
)

XMLLINT_COMMAND = "xmllint --noout --schema {0} {1} 2>&1"

try:
    from lxml import etree
except ImportError:
    etree = None


class XsdValidator(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def validate(self, schema_path, target_path):
        """ Validate ``target_path`` against ``schema_path``.

        :return type: ValidationResult
        """

    @abc.abstractmethod
    def enabled(self):
        """ Return True iff system has dependencies for this validator.

        :return type: bool
        """

ValidationResult = namedtuple("ValidationResult", ["passed", "output"])


class LxmlValidator(XsdValidator):
    """ Validate XSD files using lxml library. """

    def validate(self, schema_path, target_path):
        xsd_doc = etree.parse(schema_path)
        xsd = etree.XMLSchema(xsd_doc)
        xml = etree.parse(target_path)
        passed = xsd.validate(xml)
        return ValidationResult(passed, xsd.error_log)

    def enabled(self):
        return etree is not None


class XmllintValidator(XsdValidator):
    """ Validate XSD files with the external tool xmllint. """

    def validate(self, schema_path, target_path):
        command = XMLLINT_COMMAND.format(schema_path, target_path)
        info(command)
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        stdout, _ = p.communicate()
        passed = p.returncode == 0
        return ValidationResult(passed, stdout)

    def enabled(self):
        return bool(which("xmllint"))


VALIDATORS = [LxmlValidator(), XmllintValidator()]


def get_validator():
    for validator in VALIDATORS:
        if validator.enabled():
            return validator
