import os

from .test_utils import (
    skip_unless_module,
    skip_unless_executable,
)

from planemo.xml import validation


TEST_PATH = os.path.dirname(__file__)


@skip_unless_module("lxml")
def test_lxml_validation():
    lxml_xsd_validator = validation.LxmlValidator()
    _check_validator(lxml_xsd_validator)


@skip_unless_executable("xmllint")
def test_xmllint_validation():
    xmllint_xsd_validator = validation.XmllintValidator()
    _check_validator(xmllint_xsd_validator)


def _check_validator(xsd_validator):
    result = xsd_validator.validate(_path("xsd_schema_1.xsd"),
                                    _path("xml_good_1.xml"))
    assert result.passed, result.output
    result = xsd_validator.validate(_path("xsd_schema_1.xsd"),
                                    _path("xml_good_2.xml"))
    assert result.passed

    result = xsd_validator.validate(_path("xsd_schema_1.xsd"),
                                    _path("xml_bad_1.xml"))
    assert not result.passed
    output = result.output
    assert "not_command" in str(output), str(output)


def _path(filename):
    return os.path.join(TEST_PATH, filename)
