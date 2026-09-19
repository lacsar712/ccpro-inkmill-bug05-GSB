"""轻量级、幂等的结构补齐。

项目没有使用迁移框架（Alembic），表结构主要靠
``Base.metadata.create_all`` 创建，而它对**已存在**的表不会做任何变更。
因此历史数据库里的 ``grind_passes`` 缺少同机遍次号唯一约束，需要在启动时
显式补齐。

若表中已经存在重复的 (mill_id, pass_no) 数据，创建唯一索引会失败并抛出
异常 —— 这里刻意不静默忽略，必须先人工清理脏数据，避免继续在坏数据上运行。
"""

from sqlalchemy import Engine, text
from sqlalchemy import inspect

GRIND_PASS_UNIQUE_NAME = "uq_grind_pass_mill_pass_no"
GRIND_PASS_UNIQUE_COLS = ("mill_id", "pass_no")


def _unique_constraint_exists(inspector, table: str) -> bool:
    # 显式定义的 UNIQUE 约束（SQLite / MySQL 均可反射）
    for uc in inspector.get_unique_constraints(table):
        if uc.get("name") == GRIND_PASS_UNIQUE_NAME:
            return True
        if tuple(uc.get("column_names") or ()) == GRIND_PASS_UNIQUE_COLS:
            return True

    # MySQL 上 UNIQUE 约束也体现为唯一索引
    for idx in inspector.get_indexes(table):
        if idx.get("unique") and (
            idx.get("name") == GRIND_PASS_UNIQUE_NAME
            or tuple(idx.get("column_names") or ()) == GRIND_PASS_UNIQUE_COLS
        ):
            return True

    return False


def ensure_schema_constraints(engine: Engine) -> None:
    """幂等地补齐 grind_passes 的同机遍次号唯一约束。"""
    inspector = inspect(engine)
    table = "grind_passes"
    if table not in inspector.get_table_names():
        # create_all 尚未建表，稍后由 create_all 直接带上约束。
        return

    if _unique_constraint_exists(inspector, table):
        return

    ddl = text(
        f"CREATE UNIQUE INDEX {GRIND_PASS_UNIQUE_NAME} "
        f"ON {table} ({', '.join(GRIND_PASS_UNIQUE_COLS)})"
    )
    # 已有重复数据时这里会抛 IntegrityError，交由启动流程显式失败，不做静默处理。
    with engine.begin() as conn:
        conn.execute(ddl)
