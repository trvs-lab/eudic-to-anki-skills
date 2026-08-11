from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills" / "eudic-to-anki"


class SkillExportRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entry = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        cls.date_range = (SKILL_DIR / "workflows" / "date-range.md").read_text(
            encoding="utf-8"
        )
        cls.export_module = (
            SKILL_DIR / "modules" / "export" / "README.md"
        ).read_text(encoding="utf-8")
        cls.rules = (SKILL_DIR / "RULES_README.md").read_text(encoding="utf-8")

    def test_entry_routes_relative_and_explicit_ranges_before_export(self) -> None:
        for request_shape in ("过去一周", "最近 N 天", "连续日期范围"):
            self.assertIn(request_shape, self.entry)
        self.assertIn("workflows/date-range.md", self.entry)
        self.assertIn("workflows/yesterday.md", self.entry)
        self.assertIn("workflows/word-list.md", self.entry)

    def test_entry_does_not_duplicate_a_day_specific_export_pipeline(self) -> None:
        self.assertNotIn("scripts/eudic_export.py", self.entry)
        self.assertNotIn("_day_<D>", self.entry)

    def test_range_workflow_uses_one_command_with_both_range_boundaries(self) -> None:
        export_commands = [
            line
            for line in self.date_range.splitlines()
            if "python3 scripts/eudic_export.py" in line
        ]
        self.assertEqual(export_commands.__len__(), 1)
        command = export_commands[0]
        self.assertIn("--start-date <START>", command)
        self.assertIn("--end-date <END>", command)
        self.assertIn("_range_<START>_<END>_export.csv", command)

    def test_range_workflow_explicitly_forbids_daily_or_parallel_exports(self) -> None:
        self.assertIn("不得按天拆分", self.date_range)
        self.assertIn("不得并行", self.date_range)
        self.assertIn("一次 `eudic_export.py` 调用", self.date_range)

    def test_export_module_explains_local_filtering_and_runtime_guards(self) -> None:
        for contract in (
            "本地过滤",
            "分类查询",
            "分页请求",
            "单实例",
            "25 次／分钟",
            "Retry-After",
            "请求统计",
            "原子",
        ):
            self.assertIn(contract, self.export_module)

    def test_rules_include_a_real_multi_day_range_example(self) -> None:
        self.assertIn("--start-date 2026-05-01 --end-date 2026-05-07", self.rules)
        self.assertIn("_range_2026-05-01_2026-05-07_export.csv", self.rules)


if __name__ == "__main__":
    unittest.main()
