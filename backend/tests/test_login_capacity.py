from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore, Event
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from loja_assistente.auth import service


def test_password_slots_reject_excess_work_and_release_after_completion(monkeypatch):
    started = [Event(), Event()]
    release = Event()
    calls = []

    def verify(_hash, password):
        calls.append(password)
        started[int(password)].set()
        assert release.wait(3)
        return True

    monkeypatch.setattr(service, "PASSWORD_SLOTS", BoundedSemaphore(2))
    monkeypatch.setattr(service, "password_hasher", Mock(verify=verify))
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = [executor.submit(service.verify_password, str(i), "synthetic") for i in range(2)]
        try:
            assert all(event.wait(3) for event in started)
            with pytest.raises(HTTPException) as failure:
                service.verify_password("excess", "synthetic")
            assert failure.value.status_code == 503
            assert failure.value.headers == {"Retry-After": "1"}
            assert len(calls) == 2
        finally:
            release.set()
        assert all(future.result() for future in pending)
    assert service.verify_password("0", "synthetic")


def test_password_slot_is_released_even_when_hasher_crashes(monkeypatch):
    monkeypatch.setattr(service, "PASSWORD_SLOTS", BoundedSemaphore(1))
    hasher = Mock(verify=Mock(side_effect=[RuntimeError("synthetic"), True]))
    monkeypatch.setattr(service, "password_hasher", hasher)
    with pytest.raises(RuntimeError):
        service.verify_password("x", "synthetic")
    assert service.verify_password("x", "synthetic")
