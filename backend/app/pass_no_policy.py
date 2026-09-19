"""Pass number helpers."""

from app.models.grind_pass import GrindPass


def assert_pass_no_available(db, mill_id: int, pass_no: int, exclude_id: int | None = None) -> bool:
    """同一研磨机下遍次号是否可用。

    返回 True 表示 (mill_id, pass_no) 未被其他遍次占用；
    exclude_id 用于更新时排除当前正在编辑的行。
    """
    q = db.query(GrindPass).filter(
        GrindPass.mill_id == mill_id,
        GrindPass.pass_no == pass_no,
    )
    if exclude_id is not None:
        q = q.filter(GrindPass.id != exclude_id)
    return q.first() is None
