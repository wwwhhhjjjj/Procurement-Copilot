import streamlit as st
from PyPDF2 import PdfReader
import requests
import os


BACKEND_API_URL = os.getenv(
    "BACKEND_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


st.set_page_config(
    page_title="Medical Procurement Copilot",
    page_icon="🏥",
    layout="wide",
)

st.title("Medical Procurement Copilot 医疗设备采购智能协同助手")
st.caption("粘贴医疗设备采购报价单，由多智能体协作完成合规、库存与高价值资产审核")

access_token = st.text_input(
    "接口访问令牌",
    value="medical_admin_token",
    type="password",
)
AUTH_HEADERS = {"Authorization": f"Bearer {access_token}"}

uploaded_pdf = st.file_uploader(
    "上传采购报价单 PDF",
    type=["pdf"],
)

text_report = st.text_area(
    "采购报价单",
    height=280,
    placeholder="请粘贴供应商、产品名称、数量、单价、交付周期等报价信息...",
)

if st.button("开始分析", type="primary", use_container_width=True):
    report_text = text_report.strip()
    if uploaded_pdf is not None:
        try:
            pdf_reader = PdfReader(uploaded_pdf)
            report_text = "\n".join(
                page.extract_text() or ""
                for page in pdf_reader.pages
            ).strip()
        except Exception as exc:
            st.error(f"PDF 解析失败：{exc}")
            report_text = ""

    if not report_text.strip():
        st.warning("请上传 PDF 或粘贴采购报价单。")
    else:
        try:
            with st.spinner("4 位采购智能体正在协作分析与审批..."):
                response = requests.post(
                    f"{BACKEND_API_URL}/api/analyze",
                    json={"report_text": report_text},
                    headers=AUTH_HEADERS,
                    timeout=300,
                )
                response.raise_for_status()
                response_data = response.json()
                analysis_report = response_data.get("report", "")
                execution_time = response_data.get("execution_time", 0)
            st.subheader("多智能体最终分析报告")
            st.markdown(analysis_report)
            st.metric(
                "本次多智能体协同分析总耗时",
                f"{execution_time:.3f} 秒",
            )
        except Exception as exc:
            st.error(f"分析失败：{exc}")

st.divider()
with st.expander("查看历史采购记录"):
    try:
        response = requests.get(
            f"{BACKEND_API_URL}/api/history",
            timeout=30,
        )
        response.raise_for_status()
        records = response.json().get("records", [])
        if records:
            st.dataframe(
                [
                    {
                        "ID": record["id"],
                        "供应商": record["supplier"],
                        "总价": record["total_amount"],
                        "决策建议": record["decision_summary"],
                        "创建时间": record["created_at"],
                    }
                    for record in records
                ],
                use_container_width=True,
            )
        else:
            st.info("暂无历史采购记录。")
    except Exception as exc:
        st.error(f"无法读取历史采购记录：{exc}")
