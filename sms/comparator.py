import difflib
from abc import ABC, abstractmethod
from typing import Generic, Iterator, TypeVar

__all__ = ["Comparator", "LinesDiffComparator"]

T = TypeVar("T")
R = TypeVar("R")


def diff_bytes(old: list[bytes], new: list[bytes]) -> Iterator[bytes]:
    """
    Create a diff of two byte strings.
    """
    return difflib.diff_bytes(difflib.unified_diff, old, new, b"before", b"after")


class Comparator(ABC, Generic[T, R]):
    @abstractmethod
    def compare(self, old: T, new: T) -> R | None:
        """
        Compare two versions of an arifact and returns a comparison
        result (for instance, a diff) if the two differ according to the
        comparator's rules. Otherwise, None is returned.
        """
        ...


class LinesDiffComparator(Comparator):
    """
    Compare two byte strings by splitting them into lines and comparing
    diffing them.
    """

    def compare(self, old: bytes, new: bytes) -> Iterator[bytes]:
        oldlines = old.splitlines()
        newlines = new.splitlines()

        return diff_bytes(oldlines, newlines)
