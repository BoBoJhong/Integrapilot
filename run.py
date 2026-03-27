"""執行兩專案整合評估 Crew。"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from integrapilot.crew import create_integration_assessment_crew


def _resolve_path(p: str) -> str:
    return os.path.abspath(os.path.expanduser(p))


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="比對兩個專案路徑並產出整合評估報告（CrewAI）。"
    )
    parser.add_argument(
        "--project-a",
        required=True,
        help="專案 A 的根目錄路徑",
    )
    parser.add_argument(
        "--project-b",
        required=True,
        help="專案 B 的根目錄路徑",
    )
    args = parser.parse_args()

    a = _resolve_path(args.project_a)
    b = _resolve_path(args.project_b)
    if not os.path.isdir(a):
        print(f"錯誤：專案 A 不是有效目錄：{a}", file=sys.stderr)
        return 2
    if not os.path.isdir(b):
        print(f"錯誤：專案 B 不是有效目錄：{b}", file=sys.stderr)
        return 2

    if not os.getenv("GOOGLE_API_KEY"):
        print(
            "提示：未設定 GOOGLE_API_KEY，請在 .env 中設定（可參考 .env.example）。",
            file=sys.stderr,
        )

    crew = create_integration_assessment_crew(a, b)
    result = crew.kickoff()
    print("\n--- 最終輸出 ---\n")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
