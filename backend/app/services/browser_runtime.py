from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BrowserSession, BrowserTab, ReplayIndex, TGEProfile, WorkerNode
from app.services.playwright_runner import PlaywrightService, get_playwright_settings
from app.services.tge import TgeService, get_tge_settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BrowserAdapter(ABC):
    @abstractmethod
    def start(self, session: BrowserSession | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def attach(self, session: BrowserSession) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self, session: BrowserSession) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def open_tab(self, session: BrowserSession, url: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def close_tab(self, session: BrowserSession, tab: BrowserTab) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def current_tabs(self, session: BrowserSession) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def status(self, session: BrowserSession) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def heartbeat(self, session: BrowserSession) -> dict[str, Any]:
        raise NotImplementedError


class MockBrowserAdapter(BrowserAdapter):
    def start(self, session: BrowserSession | None = None) -> dict[str, Any]:
        return {"status": "RUNNING", "mock": True}

    def attach(self, session: BrowserSession) -> dict[str, Any]:
        return {"status": "ATTACHED", "session_id": session.id, "mock": True}

    def disconnect(self, session: BrowserSession) -> dict[str, Any]:
        return {"status": "DISCONNECTED", "session_id": session.id, "mock": True}

    def open_tab(self, session: BrowserSession, url: str) -> dict[str, Any]:
        return {"status": "OPEN", "url": url, "title": "Mock Browser Tab", "mock": True}

    def close_tab(self, session: BrowserSession, tab: BrowserTab) -> dict[str, Any]:
        return {"status": "CLOSED", "tab_id": tab.id, "mock": True}

    def current_tabs(self, session: BrowserSession) -> list[dict[str, Any]]:
        return []

    def status(self, session: BrowserSession) -> dict[str, Any]:
        return {"status": session.status, "mock": True}

    def heartbeat(self, session: BrowserSession) -> dict[str, Any]:
        return {"status": "HEALTHY", "mock": True}


class TGEBrowserAdapter(MockBrowserAdapter):
    def __init__(self, db: Session):
        self.db = db
        self.service = TgeService(get_tge_settings(db))

    def start(self, session: BrowserSession | None = None) -> dict[str, Any]:
        profile = self._profile(session)
        if not profile:
            return {"status": "RUNNING", "message": "TGE mock start without profile"}
        return self.service.start_profile(profile.tge_environment_id or profile.environment_id or "")

    def attach(self, session: BrowserSession) -> dict[str, Any]:
        profile = self._profile(session)
        if not profile:
            return {"status": "ATTACHED", "message": "TGE mock attach without profile"}
        return self.service.attach_profile(profile.tge_environment_id or profile.environment_id or "")

    def status(self, session: BrowserSession) -> dict[str, Any]:
        profile = self._profile(session)
        if not profile:
            return {"status": session.status, "message": "No TGE profile"}
        return self.service.get_profile_status(profile.tge_environment_id or profile.environment_id or "")

    def heartbeat(self, session: BrowserSession) -> dict[str, Any]:
        return self.status(session)

    def _profile(self, session: BrowserSession | None) -> TGEProfile | None:
        if not session or not session.profile_id:
            return None
        return self.db.get(TGEProfile, session.profile_id)


class PlaywrightBrowserAdapter(MockBrowserAdapter):
    def __init__(self, db: Session):
        self.settings = get_playwright_settings(db)
        self.service = PlaywrightService(self.settings)

    def attach(self, session: BrowserSession) -> dict[str, Any]:
        websocket_url = (session.metadata_json or {}).get("websocket_url")
        return self.service.connect_to_browser(websocket_url)

    def disconnect(self, session: BrowserSession) -> dict[str, Any]:
        return self.service.disconnect()

    def open_tab(self, session: BrowserSession, url: str) -> dict[str, Any]:
        opened = self.service.open_new_tab(url)
        if opened.get("status") == "PAGE_OPENING":
            loaded = self.service.wait_for_page_load()
            return {"status": "OPEN", "url": url, "title": "Playwright Tab", "loaded": loaded}
        return opened

    def close_tab(self, session: BrowserSession, tab: BrowserTab) -> dict[str, Any]:
        return self.service.close_current_tab()


class BrowserManager:
    def __init__(self, db: Session):
        self.db = db

    def active_session(
        self,
        *,
        browser_type: str,
        worker_id: int | None = None,
        account_id: int | None = None,
        profile_id: int | None = None,
    ) -> BrowserSession | None:
        statement = select(BrowserSession).where(
            BrowserSession.browser_type == browser_type,
            BrowserSession.status.in_(["RUNNING", "ATTACHED", "RECOVERING"]),
        )
        if worker_id:
            statement = statement.where(BrowserSession.worker_id == worker_id)
        if account_id:
            statement = statement.where(BrowserSession.account_id == account_id)
        if profile_id:
            statement = statement.where(BrowserSession.profile_id == profile_id)
        return self.db.scalar(statement.order_by(BrowserSession.updated_at.desc()))

    def dead_sessions(self) -> list[BrowserSession]:
        threshold = utc_now() - timedelta(seconds=90)
        return self.db.scalars(
            select(BrowserSession).where(
                BrowserSession.status.in_(["RUNNING", "ATTACHED"]),
                BrowserSession.last_heartbeat.is_not(None),
                BrowserSession.last_heartbeat < threshold,
            )
        ).all()


class BrowserRuntime:
    def __init__(self, db: Session):
        self.db = db
        self.manager = BrowserManager(db)

    def adapter_for(self, browser_type: str) -> BrowserAdapter:
        key = browser_type.lower()
        if key == "tge":
            return TGEBrowserAdapter(self.db)
        if key == "playwright":
            return PlaywrightBrowserAdapter(self.db)
        return MockBrowserAdapter()

    def start(
        self,
        *,
        browser_type: str = "mock",
        worker_id: int | None = None,
        account_id: int | None = None,
        profile_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BrowserSession:
        existing = self.manager.active_session(
            browser_type=browser_type,
            worker_id=worker_id,
            account_id=account_id,
            profile_id=profile_id,
        )
        if existing:
            return existing
        session = BrowserSession(
            browser_type=browser_type,
            worker_id=worker_id,
            account_id=account_id,
            profile_id=profile_id,
            status="STARTING",
            started_at=utc_now(),
            last_heartbeat=utc_now(),
            metadata_json=metadata or {},
        )
        self.db.add(session)
        self.db.flush()
        result = self.adapter_for(browser_type).start(session)
        session.status = "RUNNING" if result.get("status") in {"SUCCESS", "RUNNING", "STARTING"} else str(result.get("status", "RUNNING"))
        session.metadata_json = {**(session.metadata_json or {}), "last_start": result}
        return session

    def attach(self, session_id: int) -> BrowserSession:
        session = self._session(session_id)
        result = self.adapter_for(session.browser_type).attach(session)
        session.status = "ATTACHED" if result.get("status") in {"SUCCESS", "ATTACHED"} else str(result.get("status", "BROKEN"))
        session.metadata_json = {**(session.metadata_json or {}), "last_attach": result}
        session.last_heartbeat = utc_now()
        return session

    def open_url(
        self,
        *,
        url: str,
        browser_type: str = "mock",
        worker_id: int | None = None,
        account_id: int | None = None,
        profile_id: int | None = None,
        execution_task_id: int | None = None,
    ) -> BrowserTab:
        session = self.start(
            browser_type=browser_type,
            worker_id=worker_id,
            account_id=account_id,
            profile_id=profile_id,
        )
        if session.status != "ATTACHED":
            self.attach(session.id)
        result = self.adapter_for(session.browser_type).open_tab(session, url)
        tab = BrowserTab(
            session_id=session.id,
            url=url,
            title=str(result.get("title") or url[:120]),
            status="OPEN" if result.get("status") in {"OPEN", "PAGE_OPENING"} else str(result.get("status", "OPEN")),
            opened_at=utc_now(),
            metadata_json={"adapter_result": result, "execution_task_id": execution_task_id},
        )
        self.db.add(tab)
        self.db.flush()
        session.last_heartbeat = utc_now()
        if execution_task_id:
            self.index_replay(execution_task_id, session, tab)
        return tab

    def close_tab(self, tab_id: int) -> BrowserTab:
        tab = self.db.get(BrowserTab, tab_id)
        if not tab:
            raise ValueError("browser tab not found")
        session = self._session(tab.session_id)
        result = self.adapter_for(session.browser_type).close_tab(session, tab)
        tab.status = "CLOSED" if result.get("status") in {"CLOSED", "TAB_CLOSED"} else str(result.get("status", "CLOSED"))
        tab.closed_at = utc_now()
        tab.metadata_json = {**(tab.metadata_json or {}), "close_result": result}
        session.last_heartbeat = utc_now()
        return tab

    def heartbeat(self, session_id: int) -> BrowserSession:
        session = self._session(session_id)
        result = self.adapter_for(session.browser_type).heartbeat(session)
        session.last_heartbeat = utc_now()
        if result.get("status") in {"FAILED", "BROKEN", "ATTACH_FAILED"}:
            session.status = "BROKEN"
        return session

    def disconnect(self, session_id: int) -> BrowserSession:
        session = self._session(session_id)
        result = self.adapter_for(session.browser_type).disconnect(session)
        session.status = "DISCONNECTED" if result.get("status") in {"DISCONNECTED", "SUCCESS"} else str(result.get("status", "DISCONNECTED"))
        session.closed_at = utc_now()
        session.metadata_json = {**(session.metadata_json or {}), "last_disconnect": result}
        return session

    def recover(self, session_id: int) -> BrowserSession:
        session = self._session(session_id)
        session.status = "RECOVERING"
        result = self.adapter_for(session.browser_type).attach(session)
        if result.get("status") in {"SUCCESS", "ATTACHED"}:
            session.status = "RUNNING"
            session.last_heartbeat = utc_now()
        else:
            session.status = "BROKEN"
        session.metadata_json = {**(session.metadata_json or {}), "last_recover": result}
        return session

    def index_replay(self, execution_task_id: int, session: BrowserSession, tab: BrowserTab) -> ReplayIndex:
        replay = self.db.scalar(select(ReplayIndex).where(ReplayIndex.execution_task_id == execution_task_id))
        manifest = {
            "session_id": session.id,
            "tab_id": tab.id,
            "browser_type": session.browser_type,
            "url": tab.url,
            "screenshot": None,
            "html": None,
            "console": None,
            "network": None,
        }
        if replay:
            replay.manifest_json = {**(replay.manifest_json or {}), **manifest}
            replay.status = "INDEXED"
        else:
            replay = ReplayIndex(
                execution_task_id=execution_task_id,
                status="INDEXED",
                artifact_count=0,
                manifest_json=manifest,
            )
            self.db.add(replay)
        self.db.flush()
        return replay

    def runtime_status(self) -> dict[str, Any]:
        running = self.db.scalar(select(func.count()).select_from(BrowserSession).where(BrowserSession.status.in_(["RUNNING", "ATTACHED"]))) or 0
        tabs = self.db.scalar(select(func.count()).select_from(BrowserTab).where(BrowserTab.status == "OPEN")) or 0
        dead = len(self.manager.dead_sessions())
        workers = self.db.scalar(select(func.count()).select_from(WorkerNode).where(WorkerNode.status == "ONLINE")) or 0
        return {
            "runtime": "BROWSER",
            "running_browsers": running,
            "running_tabs": tabs,
            "dead_sessions": dead,
            "workers": workers,
            "automation_boundary": "Execution -> BrowserRuntime -> BrowserAdapter",
        }

    def _session(self, session_id: int) -> BrowserSession:
        session = self.db.get(BrowserSession, session_id)
        if not session:
            raise ValueError("browser session not found")
        return session
