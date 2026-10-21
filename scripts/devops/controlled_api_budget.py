"""受控 API 的 owner-only SQLite 持久预算；认领先于发送，不退款、不重试。

lifecycle: permanent
信任 Controller 和 owner 文件系统，不宣称能抵御具有同 UID 写权限的恶意主体。
"""

from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid

from scripts.devops.controlled_api_policy import (
    CHANNEL,
    ControlError,
    positive_int,
    source_identity,
    validate_plan,
)
from scripts.devops.independent_review_protocol import canonical_json

STATE_DIRECTORY_MODE = 0o700
STATE_FILE_MODE = 0o600
MAX_AUTHORIZED_PLANS = 100
STATE_MARKER = b"controlled-api-private-execution-state/v1\n"
APPLICATION_ID = 0x43504149


class Budget:
    """同一任务所有 Provider/块共享不可重置的请求、Token 和条件性 USD 预算。"""

    def __init__(self, root: Path, *, initialize: bool = False):
        self.root = Path(root).absolute()
        if any(path.is_symlink() for path in (self.root, *self.root.parents)):
            raise ControlError("UNSAFE_STATE_PATH")
        if initialize:
            self.root.mkdir(mode=STATE_DIRECTORY_MODE, parents=False, exist_ok=False)
            marker = self.root / ".execution-state"
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, STATE_FILE_MODE)
            with os.fdopen(fd, "wb") as stream:
                stream.write(STATE_MARKER)
                stream.flush()
                os.fsync(stream.fileno())
        elif not self.root.is_dir():
            raise ControlError("STATE_MISSING_NO_AUTOMATIC_RESET")
        info = self.root.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != STATE_DIRECTORY_MODE:
            raise ControlError("UNSAFE_STATE_DIRECTORY")
        self.path = self.root / "budget.sqlite3"
        self._initializing = initialize
        flags = os.O_RDWR | os.O_NOFOLLOW
        if initialize:
            flags |= os.O_CREAT | os.O_EXCL
        fd = os.open(self.path, flags, STATE_FILE_MODE)
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != STATE_FILE_MODE
                or info.st_nlink != 1
            ):
                raise ControlError("UNSAFE_STATE_FILE")
        finally:
            os.close(fd)
        with closing(self.connect()) as db:
            if not initialize:
                if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                    raise ControlError("STATE_VERSION_UNKNOWN")
                return
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks(
                  identity TEXT PRIMARY KEY, execution TEXT UNIQUE NOT NULL, source BLOB NOT NULL,
                  request_cap INTEGER NOT NULL, token_cap INTEGER NOT NULL, money_cap INTEGER NOT NULL,
                  requests INTEGER NOT NULL DEFAULT 0, tokens INTEGER NOT NULL DEFAULT 0,
                  money INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS slots(
                  task TEXT NOT NULL, slot INTEGER NOT NULL, plan BLOB NOT NULL,
                  state TEXT NOT NULL, category TEXT, response_sha256 TEXT,
                  PRIMARY KEY(task, slot));
                CREATE TRIGGER IF NOT EXISTS no_task_delete BEFORE DELETE ON tasks
                  BEGIN SELECT RAISE(ABORT, 'immutable task'); END;
                CREATE TRIGGER IF NOT EXISTS no_budget_reset BEFORE UPDATE ON tasks
                  WHEN NEW.identity != OLD.identity OR NEW.execution != OLD.execution
                  OR NEW.source != OLD.source OR NEW.request_cap != OLD.request_cap
                  OR NEW.token_cap != OLD.token_cap OR NEW.money_cap != OLD.money_cap
                  OR NEW.requests < OLD.requests OR NEW.tokens < OLD.tokens OR NEW.money < OLD.money
                  OR NEW.requests > NEW.request_cap OR NEW.tokens > NEW.token_cap OR NEW.money > NEW.money_cap
                  BEGIN SELECT RAISE(ABORT, 'immutable budget'); END;
                CREATE TRIGGER IF NOT EXISTS no_slot_delete BEFORE DELETE ON slots
                  BEGIN SELECT RAISE(ABORT, 'immutable slot'); END;
                CREATE TRIGGER IF NOT EXISTS no_slot_replay BEFORE UPDATE ON slots
                  WHEN NEW.task != OLD.task OR NEW.slot != OLD.slot OR NEW.plan != OLD.plan
                  OR NOT ((OLD.state = 'PLANNED' AND NEW.state = 'CLAIMED')
                       OR (OLD.state = 'CLAIMED' AND NEW.state IN ('COMPLETE', 'UNKNOWN')))
                  BEGIN SELECT RAISE(ABORT, 'immutable claim'); END;
                PRAGMA user_version=1;
                PRAGMA application_id=1129333065;
            """)
        self._initializing = False

    def _guard_state(self) -> None:
        """只写本组件新建的私有执行状态，不接受其他 SQLite/Receipt/Ledger。"""
        if any(path.is_symlink() for path in (self.root, *self.root.parents)):
            raise ControlError("UNSAFE_STATE_PATH")
        for path, mode in ((self.root, STATE_DIRECTORY_MODE), (self.path, STATE_FILE_MODE)):
            info = path.lstat()
            expected_type = stat.S_ISDIR if path == self.root else stat.S_ISREG
            if (
                not expected_type(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != mode
                or (path == self.path and info.st_nlink != 1)
            ):
                raise ControlError("UNSAFE_STATE_FILE")
        marker = self.root / ".execution-state"
        fd = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != STATE_FILE_MODE
                or info.st_nlink != 1
                or stream.read(len(STATE_MARKER) + 1) != STATE_MARKER
            ):
                raise ControlError("EXECUTION_STATE_IDENTITY_REQUIRED")

    def connect(self) -> sqlite3.Connection:
        """每次操作单独连接，使用 FULL 同步与 SQLite 文件锁跨进程串行化。"""
        # mode=rw 禁止恢复时悄悄新建空账本；目录也不可由普通 Runner 自动重建。
        self._guard_state()
        db = sqlite3.connect(
            self.path.as_uri() + "?mode=rw", uri=True, timeout=10, isolation_level=None
        )
        db.execute("PRAGMA synchronous=FULL")
        if (
            not self._initializing
            and db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
        ):
            db.close()
            raise ControlError("EXECUTION_STATE_IDENTITY_REQUIRED")
        return db

    def create(
        self, source: dict, plans: list[dict], *, requests: int, tokens: int, nano_usd: int
    ) -> str:
        """Controller 的一次性任务建账；同候选身份重复创建一律拒绝。"""
        identity = source_identity(source)
        for value in (requests, tokens, nano_usd):
            positive_int(value)
        if not isinstance(plans, list) or not plans or len(plans) > MAX_AUTHORIZED_PLANS:
            raise ControlError("INVALID_AUTHORIZED_PLANS")
        frozen_plans = [canonical_json(validate_plan(plan)) for plan in plans]
        with closing(self.connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "INSERT INTO tasks(identity,execution,source,request_cap,token_cap,money_cap) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        identity,
                        str(uuid.uuid4()),
                        canonical_json(source),
                        requests,
                        tokens,
                        nano_usd,
                    ),
                )
                db.executemany(
                    "INSERT INTO slots VALUES(?,?,?,'PLANNED',NULL,NULL)",
                    [(identity, index, plan) for index, plan in enumerate(frozen_plans, 1)],
                )
                db.execute("COMMIT")
            except sqlite3.IntegrityError:
                db.execute("ROLLBACK")
                raise ControlError("TASK_ALREADY_EXISTS") from None
        return identity

    def claim(self, identity: str, slot: int, plan: dict) -> None:
        """发送前不可逆事务；崩溃窗口按已消费处理，即使实际上尚未发送。"""
        positive_int(slot)
        plan = validate_plan(plan)
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT request_cap,token_cap,money_cap,requests,tokens,money FROM tasks "
                "WHERE identity=?",
                (identity,),
            ).fetchone()
            if not row:
                raise ControlError("UNKNOWN_TASK")
            saved = db.execute(
                "SELECT plan,state FROM slots WHERE task=? AND slot=?", (identity, slot)
            ).fetchone()
            if not saved or saved[0] != canonical_json(plan):
                raise ControlError("UNAUTHORIZED_REQUEST")
            if saved[1] != "PLANNED":
                raise ControlError("REQUEST_ALREADY_CLAIMED")
            request_cap, token_cap, money_cap, used, tokens, money = row
            if used >= request_cap:
                raise ControlError("REQUEST_CAP_EXHAUSTED")
            if tokens + plan["reserve_tokens"] > token_cap:
                raise ControlError("TOKEN_CAP_EXHAUSTED")
            if money + plan["reserve_nano_usd"] > money_cap:
                raise ControlError("MONEY_CAP_EXHAUSTED")
            db.execute("UPDATE slots SET state='CLAIMED' WHERE task=? AND slot=?", (identity, slot))
            db.execute(
                "UPDATE tasks SET requests=requests+1,tokens=tokens+?,money=money+? WHERE identity=?",
                (plan["reserve_tokens"], plan["reserve_nano_usd"], identity),
            )

    def finish(
        self, identity: str, slot: int, *, complete: bool, category: str, response_sha256: str
    ) -> None:
        """不释放任何预留；Usage 缺失/超限/响应丢失均不能使任务重新获得额度。"""
        with closing(self.connect()) as db:
            result = db.execute(
                "UPDATE slots SET state=?,category=?,response_sha256=? "
                "WHERE task=? AND slot=? AND state='CLAIMED'",
                ("COMPLETE" if complete else "UNKNOWN", category, response_sha256, identity, slot),
            )
            if result.rowcount != 1:
                raise ControlError("INVALID_COMPLETION")

    def evidence(self, identity: str) -> dict:
        """独立 execution evidence，不能作为正式 Review Receipt。"""
        with closing(self.connect()) as db:
            row = db.execute(
                "SELECT execution,source,requests,tokens,money,request_cap,token_cap,money_cap FROM tasks WHERE identity=?",
                (identity,),
            ).fetchone()
            if not row:
                raise ControlError("UNKNOWN_TASK")
            slots = db.execute(
                "SELECT slot,state,category,response_sha256,plan FROM slots WHERE task=? ORDER BY slot",
                (identity,),
            ).fetchall()
        return {
            "schema": "controlled-api-execution-evidence/v1",
            "channel": CHANNEL,
            "identity": identity,
            "execution": row[0],
            "source": json.loads(row[1]),
            "claimed_requests": row[2],
            "reserved_tokens": row[3],
            "reserved_nano_usd": row[4],
            "caps": {"requests": row[5], "tokens": row[6], "nano_usd": row[7]},
            "currency": "USD",
            "slots": [
                {
                    **dict(
                        zip(("slot", "state", "category", "response_sha256"), item[:4], strict=True)
                    ),
                    "request_sha256": json.loads(item[4])["request_sha256"],
                    "policy_sha256": json.loads(item[4])["policy_sha256"],
                    "provider": json.loads(item[4])["policy"]["provider"],
                    "model": json.loads(item[4])["policy"]["model"],
                }
                for item in slots
            ],
            "current_approval_eligible": False,
            "qualification_required": True,
            "physical_usd_bound": "NOT_PROVEN",
            "mode": "OFFLINE_ONLY",
        }
