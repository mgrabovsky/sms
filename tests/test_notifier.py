from unittest import TestCase

from sms.notifier import generate_hash, is_modified


class IsModifiedTestCase(TestCase):
    def test_empty(self) -> None:
        empty_blob = b""
        empty_hash = generate_hash(empty_blob)
        self.assertFalse(is_modified(empty_blob, empty_hash))

    def test_non_empty(self) -> None:
        empty_blob = b""
        empty_hash = generate_hash(empty_blob)
        self.assertTrue(is_modified(b"non empty text", empty_hash))
