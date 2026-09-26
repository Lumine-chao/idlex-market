"""举报：商品/用户/消息举报，凭证、进度"""
import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from .. import errors
from ..deps import get_current_user_async
from ..models import User, Report
from ..schemas import ReportReq

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _ok(data=None, message="ok"):
    return {"code": 0, "message": message, "data": data}


def _parse_evidence(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else [str(val)]
    except Exception:
        return [raw]


def _report_out(r: Report) -> dict:
    return {
        "id": r.id, "targetType": r.target_type, "targetId": r.target_id,
        "reasonType": r.reason_type, "description": r.description,
        "evidence": _parse_evidence(r.evidence),
        "status": r.status, "result": r.result,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
    }


@router.post("", name="submit_report")
async def submit_report(req: ReportReq, user: User = Depends(get_current_user_async),
                        db: AsyncSession = Depends(get_db)):
    if not req.reason_type:
        raise errors.error(errors.ErrorCodes.REPORT_TYPE_REQUIRED, "report.type")
    evidence = req.evidence or []
    if len(evidence) > 3:
        evidence = evidence[:3]
    r = Report(reporter_id=user.id, target_type=req.target_type, target_id=req.target_id,
               reason_type=req.reason_type, description=req.description,
               evidence=json.dumps(evidence, ensure_ascii=False) if evidence else None,
               status=0)
    db.add(r)
    await db.commit()
    return _ok(_report_out(r), "举报已提交，平台将尽快处理")


@router.get("/mine")
async def my_reports(user: User = Depends(get_current_user_async),
                     db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Report).where(Report.reporter_id == user.id)
                             .order_by(Report.created_at.desc()))).scalars().all()
    return _ok({"list": [_report_out(r) for r in rows], "total": len(rows)})