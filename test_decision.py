import unittest

from agents import _extract_decision


class ExtractDecisionTests(unittest.TestCase):
    def test_approval_with_rejection_reason_section(self) -> None:
        report = """
        最终结论：同意采购（附条件批准）
        四、驳回原因
        无。本项目不存在驳回情形。
        审批意见：同意采购。
        """
        self.assertEqual(_extract_decision(report), "同意采购")

    def test_explicit_rejection(self) -> None:
        report = "最终结论：驳回\n驳回原因：资质无效"
        self.assertEqual(_extract_decision(report), "驳回")


if __name__ == "__main__":
    unittest.main()
