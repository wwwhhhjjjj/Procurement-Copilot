import json
import os
import re

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Task
import requests
from database import insert_record

try:
    from crewai.tools import tool
except ImportError:
    from crewai_tools import tool


load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001").rstrip("/")


@tool("query_inventory")
def query_inventory(product_name: str) -> str:
    """通过 MCP Server 查询企业 ERP 模拟库存，并返回 JSON 字符串。"""
    response = requests.get(
        f"{MCP_SERVER_URL}/api/inventory",
        params={"product": product_name},
        timeout=10,
    )
    response.raise_for_status()
    return json.dumps(response.json(), ensure_ascii=False)


@tool("query_policy")
def query_policy(query: str = "") -> str:
    """通过 MCP Server 读取企业采购合规文件，并返回完整政策内容。"""
    response = requests.get(f"{MCP_SERVER_URL}/api/policy", timeout=10)
    response.raise_for_status()
    return response.json().get("content", "")


def _create_llm() -> LLM:
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
    return LLM(
        model="openai/deepseek-chat",
        api_key=api_key,
        base_url=api_base,
    )


def _extract_supplier(report_text: str, final_result: str) -> str:
    for text in (report_text, final_result):
        match = re.search(r"(?:供应商|供应商名称)\s*[：:]\s*(.+)", text)
        if match:
            return match.group(1).strip().splitlines()[0].strip(" ，,;")
    return "未知供应商"


def _extract_total_amount(report_text: str, final_result: str) -> float:
    amounts = []
    for text in (report_text, final_result):
        matches = re.findall(
            r"(?:总价|总金额|总计|合同金额|合计)\s*[：:]\s*￥?\s*([\d,]+(?:\.\d+)?)",
            text,
        )
        for value in matches:
            try:
                amounts.append(float(value.replace(",", "")))
            except ValueError:
                pass

        for line in text.splitlines():
            quantity_match = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:台|件|套|个|批|箱|包)",
                line,
            )
            price_match = re.search(
                r"(?:单价|价格)\s*[：:：]?\s*￥?\s*([\d,]+(?:\.\d+)?)",
                line,
            )
            if quantity_match and price_match:
                try:
                    amounts.append(
                        float(quantity_match.group(1))
                        * float(price_match.group(1).replace(",", ""))
                    )
                except ValueError:
                    pass

    return max(amounts, default=0.0)


def _extract_decision(final_result: str) -> str:
    approval_match = re.search(
        r"(?:最终结论|审批意见|审批结论)\s*[：:]\s*(同意采购|驳回)",
        final_result,
    )
    if approval_match:
        return approval_match.group(1)

    final_lines = [line.strip() for line in final_result.splitlines() if line.strip()]
    for line in reversed(final_lines):
        if "同意采购" in line and "驳回" not in line:
            return "同意采购"
        if re.search(r"(?:驳回|拒绝)(?:采购)?", line) and "不构成" not in line:
            return "驳回"

    if re.search(r"(?:最终结论|审批意见|审批结论)[^。\n]*同意采购", final_result):
        return "同意采购"
    if re.search(r"(?:最终结论|审批意见|审批结论)[^。\n]*驳回", final_result):
        return "驳回"
    return final_result[:500]


def run_analysis(report_text: str) -> str:
    """解析采购报价单，完成合规、库存和审批流程，并持久化审批结果。"""
    if not report_text or not report_text.strip():
        raise ValueError("报价单文本不能为空")

    llm = _create_llm()

    procurement_analyst = Agent(
        role="医疗设备采购分析师",
        goal="准确解析医疗设备报价单，提取设备名称、型号、数量、单价、供应商、保修期和资质信息",
        backstory="你专注医疗设备采购，熟悉核磁共振仪、CT机、呼吸机和心电监护仪等设备参数、采购场景及异常报价识别。",
        llm=llm,
        verbose=True,
    )

    inventory_manager = Agent(
        role="医疗设备库存与资产管理员",
        goal="查询医院医疗设备库存，结合临床需求和资产周转情况给出采购数量及高价值资产风险建议",
        backstory="你负责医院医疗设备资产与库存管理，熟悉设备闲置、科室需求、维保周期及大型设备补货风险。",
        llm=llm,
        tools=[query_inventory],
        verbose=True,
    )

    compliance_expert = Agent(
        role="医疗设备采购合规专家",
        goal="依据医疗设备采购政策审查供应商资质、医疗器械经营许可证、注册证、保修和招采合规性",
        backstory="你负责医疗器械采购合规审查，严格核验医疗器械经营许可证、产品注册资质、原厂保修及价格合规要求。",
        llm=llm,
        tools=[query_policy],
        verbose=True,
    )

    procurement_director = Agent(
        role="医疗设备采购总监",
        goal="审查合规、库存、保修、资质和设备资产风险，给出明确的最终采购审批意见",
        backstory="你负责医院高价值医疗设备采购审批，必须综合临床价值、原厂资质、保修承诺、合规风险及投资回报后批准或驳回。",
        llm=llm,
        verbose=True,
    )

    parse_task = Task(
        description=(
            "请完整阅读以下医疗设备采购报价单，并以结构化方式提取设备名称、型号、数量、"
            "单价、总价、供应商、交付周期、原厂保修期和资质承诺：\n\n"
            f"{report_text}"
        ),
        expected_output="包含医疗设备型号、数量、价格、供应商、保修期和资质承诺的结构化采购报价摘要。",
        agent=procurement_analyst,
    )

    decision_task = Task(
        description=(
            "根据采购分析师的解析结果，为每台医疗设备调用 query_inventory 工具查询库存，"
            "结合报价价格、现有资产、临床需求、设备维护风险和高价值资产折旧，给出采购建议。"
            "请明确说明建议采购数量、库存是否充足、是否议价以及医疗资产管理理由。"
        ),
        expected_output="每种医疗设备的库存状态、采购建议、议价建议和资产风险报告。",
        agent=inventory_manager,
        context=[parse_task],
    )

    compliance_task = Task(
        description=(
            "调用 query_policy 工具读取真实医疗设备采购合规政策。依据政策逐项审查报价单、"
            "供应商医疗器械经营许可证、产品注册资质、原厂保修、采购金额和前述采购分析，"
            "识别资质或保修不合规问题并给出风险等级和结论。"
        ),
        expected_output="基于真实医疗设备采购政策的资质审查、保修审查、合规结论和风险等级。",
        agent=compliance_expert,
        context=[parse_task],
    )

    approval_task = Task(
        description=(
            "审查医疗设备采购分析师、合规专家和库存资产管理员的全部结果。"
            "综合成本、库存、临床需求、供应资质、保修承诺和合规风险，"
            "最终只给出明确审批结论：同意采购或驳回，并说明批准条件、驳回原因和下一步措施。"
            "报告开头必须写明供应商名称、采购总价以及最终结论。"
        ),
        expected_output="采购总监审批报告，包含供应商、采购总价、最终结论和具体理由。",
        agent=procurement_director,
        context=[parse_task, compliance_task, decision_task],
    )

    crew = Crew(
        agents=[
            procurement_analyst,
            compliance_expert,
            inventory_manager,
            procurement_director,
        ],
        tasks=[parse_task, compliance_task, decision_task, approval_task],
        verbose=True,
    )

    result = crew.kickoff()
    final_result = str(result)

    supplier = _extract_supplier(report_text, final_result)
    total_amount = _extract_total_amount(report_text, final_result)
    decision_summary = _extract_decision(final_result)
    insert_record(supplier, total_amount, decision_summary)

    return final_result


if __name__ == "__main__":
    sample_report = """
    供应商：华康医疗设备有限公司
    报价：
    CT机 1 台，单价 800万元，原厂保修 5 年
    心电监护仪 10 台，单价 25000 元，原厂保修 3 年
    医疗器械经营许可证：有效
    交付周期：60 天
    """
    print(run_analysis(sample_report))
