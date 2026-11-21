import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from agents import run_analysis
from database import get_records


app = FastAPI(title="Procurement Copilot Backend", version="1.0.0")
security = HTTPBearer(auto_error=False)
MEDICAL_ADMIN_TOKEN = "medical_admin_token"


class AnalyzeRequest(BaseModel):
    report_text: str = Field(..., min_length=1)


def verify_medical_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> None:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or credentials.credentials != MEDICAL_ADMIN_TOKEN
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/api/analyze")
def analyze(
    request: AnalyzeRequest,
    _auth: None = Depends(verify_medical_admin),
):
    start_time = time.time()
    try:
        result = run_analysis(request.report_text)
        execution_time = round(time.time() - start_time, 3)
        return {
            "success": True,
            "report": result,
            "execution_time": execution_time,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"分析失败：{exc}") from exc


@app.get("/api/history")
def history():
    records = get_records()
    return {
        "success": True,
        "records": [
            {
                "id": record[0],
                "supplier": record[1],
                "total_amount": record[2],
                "decision_summary": record[3],
                "created_at": record[4],
            }
            for record in records
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000)
