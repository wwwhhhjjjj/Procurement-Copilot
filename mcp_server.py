from pathlib import Path

from fastapi import FastAPI, HTTPException, Query


app = FastAPI(title="Procurement MCP Server", version="1.0.0")

INVENTORY = {
    "核磁共振仪": 3,
    "心电监护仪": 50,
    "CT机": 5,
    "呼吸机": 20,
}


@app.get("/api/inventory")
def get_inventory(product: str = Query(..., min_length=1)):
    if product in INVENTORY:
        quantity = INVENTORY[product]
    else:
        quantity = next(
            (value for name, value in INVENTORY.items() if product in name or name in product),
            0,
        )
        if quantity == 0:
            return {"product": product, "quantity": 0, "available": False}

    return {
        "product": product,
        "quantity": quantity,
        "available": quantity > 0,
    }


@app.get("/api/policy")
def get_policy():
    policy_path = Path(__file__).resolve().parent / "company_policy.txt"
    if not policy_path.exists():
        raise HTTPException(status_code=404, detail="company_policy.txt 不存在")
    return {
        "content": policy_path.read_text(encoding="utf-8"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mcp_server:app", host="0.0.0.0", port=8001, reload=True)
