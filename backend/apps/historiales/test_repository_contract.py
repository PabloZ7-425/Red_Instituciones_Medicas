from unittest import TestCase

from apps.historiales.testing.memory import MemoryHarness
from apps.historiales.testing.repository_contract import RepositoryContract


class MemoryContractTests(RepositoryContract, TestCase):
    """B1 validates the reusable suite with an explicit double, not a real engine."""
    def make_harness(self):
        return MemoryHarness()
