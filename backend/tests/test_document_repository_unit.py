"""Mocked unit tests for document_repository — no live Postgres needed. Pins
delete_all_documents' return value now that the unreachable dead code after its
return statement has been removed."""
import pytest
from unittest.mock import AsyncMock, patch
from src.repositories import document_repository


class FakeCursor:
    def __init__(self, rowcount):
        self.rowcount = rowcount


class FakeConn:
    def __init__(self, rowcount):
        self._rowcount = rowcount

    async def execute(self, *args, **kwargs):
        return FakeCursor(self._rowcount)


class FakeConnCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self, rowcount):
        self._rowcount = rowcount

    def connection(self):
        return FakeConnCtx(FakeConn(self._rowcount))


@pytest.mark.asyncio
async def test_delete_all_documents_returns_rowcount():
    fake_pool = FakePool(rowcount=3)
    with patch.object(document_repository, "get_pool", AsyncMock(return_value=fake_pool)):
        deleted = await document_repository.delete_all_documents("user-123")
    assert deleted == 3


@pytest.mark.asyncio
async def test_delete_all_documents_returns_zero_when_nothing_to_delete():
    fake_pool = FakePool(rowcount=0)
    with patch.object(document_repository, "get_pool", AsyncMock(return_value=fake_pool)):
        deleted = await document_repository.delete_all_documents("user-456")
    assert deleted == 0