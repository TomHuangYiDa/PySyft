
import yaml
import pytest
from pathlib import Path

from syftbox.lib.lib import PermissionRule, PermissionFile, PermissionType, PermissionParsingError



def test_parsing():
    yaml_string = """
    - permissions: read
    path: x.txt
    user: user@example.org
    
    - permissions: [read, write]
    path: x.txt
    user: "*"
    type: disallow
    terminal: true
    """
    rule = PermissionRule.from_rule_dict(Path("."), yaml.safe_load(yaml_string)[0], priority=0)
    file = PermissionFile.from_string(yaml_string, ".")
    assert len(file.rules) == 2

    assert file.rules[0].permissions == [PermissionType.READ]
    assert file.rules[0].path == "x.txt"
    assert file.rules[0].user == "user@example.org"
    assert file.rules[0].allow == True
    assert file.rules[0].terminal == False


    #check the same for the second rule
    assert file.rules[1].permissions == [PermissionType.READ, PermissionType.WRITE]
    assert file.rules[1].path == "x.txt"
    assert file.rules[1].user == "*"
    assert file.rules[1].allow == False
    assert file.rules[1].terminal == True


def test_parsing_fails():
    yaml_string = """
    - permissions: read
    path: "../*/x.txt"
    user: user@example.org
    """
    with pytest.raises(PermissionParsingError):
        PermissionFile.from_string(yaml_string, ".")
        
        
    def test_parsing_useremail():
        yaml_string = """
    - permissions: read
    path: "{useremail}/*"
    user: user@example.org
    """
    file = PermissionFile.from_string(yaml_string, ".")
    rule = file.rules[0]
    assert rule.has_email_template
    assert rule.resolve_path_pattern("user@example.org") == "user@example.org/*"

