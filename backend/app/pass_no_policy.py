"""Pass number helpers."""

from app.models.grind_pass import GrindPass


def assert_pass_no_available(db, mill_id: int, pass_no: int, exclude_id: int | None = None) -> bool:
    """同一研磨机下 pass_no 必须唯一。

    返回 True 表示该遍次号可用（未被其它记录占用）；
    更新时传入 exclude_id 以排除自身记录。
    """
    query = db.query(GrindPass.id).filter(
        GrindPass.mill_id == mill_id,
        GrindPass.pass_no == pass_no,
    )
    if exclude_id is not None:
        query = query.filter(GrindPass.id != exclude_id)
    return query.first() is None
