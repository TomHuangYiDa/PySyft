# stdlib

# third party
import pytest
from pytest import FixtureRequest

# syft absolute
import syft as sy


@pytest.mark.parametrize(
    "obj_name",
    [
        "mock_message",
        "mock_create_message",
        # "message_stash", # 🟡 TODO: Fix serde for KVDocumentPartition
        # "message_service",
    ],
)
def test_message_serde(obj_name: str, request: FixtureRequest) -> None:
    obj = request.getfixturevalue(obj_name)
    ser_data = sy.serialize(obj, to_bytes=True)
    assert isinstance(ser_data, bytes)
    deser_data = sy.deserialize(ser_data, from_bytes=True)

    assert isinstance(deser_data, type(obj))
    assert deser_data == obj
