from __future__ import annotations

from nzhem.ports import ReferenceDataRefresher, ReferenceRefreshResult


class RefreshReferenceService:
    """Cloud-independent entry point shared by both deployment hosts."""

    def __init__(self, refresher: ReferenceDataRefresher) -> None:
        self._refresher = refresher

    def run(self) -> ReferenceRefreshResult:
        return self._refresher.refresh()
