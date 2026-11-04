# AI contribution: 50% or more AI-generated
"""Tests for the PR policy check (FIX-26). Run: python3 -m unittest discover -s .github/scripts"""

import pathlib
import unittest
import unittest.mock

import pr_policy
from pr_policy import ChangedFile, PullRequest

TEMPLATE = (
    pathlib.Path(__file__).parent.parent / "pull_request_template.md"
).read_text(encoding="utf-8")

GOOD_BODY = """Closes #648

## What changes
Splits post_listing.

## How it was tested
New tests for the storage failure.

## AI contribution
Level: Below 50% AI-generated

AI-assisted files:
- `backend/modules/listings/services.py`

## Checklist
- [x] Every source file I added or changed starts with its AI contribution line
"""

HEADER = "# AI contribution: Below 50% AI-generated\n"


def make_pr(**overrides) -> PullRequest:
    values = {
        "title": "[PR] FIX-01: Split post_listing",
        "body": GOOD_BODY,
        "author": "markantoun0",
        "base": "main",
        "default_branch": "main",
        "closing": [648],
        "files": [
            ChangedFile(
                "backend/modules/listings/services.py",
                "modified",
                HEADER + "def f():\n    pass\n",
            ),
            ChangedFile(
                "backend/modules/listings/tests/test_services.py",
                "modified",
                HEADER + "def test_f():\n",
            ),
        ],
    }
    values.update(overrides)
    return PullRequest(**values)


class TitleTests(unittest.TestCase):
    def test_accepts_pr_prefix_and_each_id_form(self):
        for title in (
            "[PR] US-17: Walk-in registration",
            "[PR] FIX-03: Split decide_for_household",
            "[PR] FIX-03.2: Cover the boundary",
            "[PR] T-05.33.3: Post listing service",
            "[PR] SET-17: Azure staging",
            "[PR] ES-01: Accounts",
            "[PR] US-12, US-13: Partner applications",
        ):
            with self.subTest(title=title):
                self.assertEqual(pr_policy.check_title(title), [])

    def test_refuses_other_formats(self):
        for title in (
            "[US-17] Walk-in registration",
            "[PR] US-17 feat(households): walk-in",
            "{PR] SET-12: Listing categories",
            "[PR] Set 08 low income thresholds",
            "[PR] - Set 07 ruleset version",
            "[PR] US-17:",
            "[PR] US-17:  ",
            "SET-18 feat(seed): add the dataset",
            "[PR] FIX-1: one digit",
        ):
            with self.subTest(title=title):
                errors = pr_policy.check_title(title)
                self.assertEqual(len(errors), 1)
                self.assertIn("[PR] <ID>: <summary>", errors[0])


class LinkTests(unittest.TestCase):
    def test_pull_request_into_main_must_close_an_issue(self):
        self.assertEqual(pr_policy.check_link(make_pr(closing=[648])), [])
        errors = pr_policy.check_link(make_pr(closing=[], body="Refs #596"))
        self.assertEqual(len(errors), 1)
        self.assertIn("Closes #<issue>", errors[0])

    def test_pull_request_into_another_branch_needs_a_reference(self):
        into_story = {"base": "US-17", "closing": []}
        self.assertEqual(
            pr_policy.check_link(make_pr(body="Part of #461", **into_story)), []
        )
        self.assertEqual(
            len(pr_policy.check_link(make_pr(body="No issue here", **into_story))), 1
        )

    def test_reference_inside_a_comment_does_not_count(self):
        pr = make_pr(base="US-17", closing=[], body="<!-- Part of #461 -->")
        self.assertEqual(len(pr_policy.check_link(pr)), 1)

    def test_html_entity_is_not_an_issue_reference(self):
        pr = make_pr(base="US-17", closing=[], body="Uses &#39; quotes")
        self.assertEqual(len(pr_policy.check_link(pr)), 1)


class AiDeclarationTests(unittest.TestCase):
    def test_complete_section_passes(self):
        self.assertEqual(pr_policy.check_ai(make_pr()), [])

    def test_untouched_template_fails(self):
        errors = pr_policy.check_ai(make_pr(body=TEMPLATE))
        self.assertEqual(len(errors), 1)
        self.assertIn("exactly one level", errors[0])

    def test_missing_section_fails(self):
        errors = pr_policy.check_ai(make_pr(body="Closes #648\n\nJust code."))
        self.assertIn("Add an `## AI contribution` section", errors[0])

    def test_two_levels_fail(self):
        body = GOOD_BODY.replace(
            "Level: Below 50% AI-generated",
            "Level: Below 50% AI-generated or 50% or more AI-generated",
        )
        self.assertIn("Found 2", pr_policy.check_ai(make_pr(body=body))[0])

    def test_ai_level_needs_a_listed_changed_file(self):
        body = GOOD_BODY.replace("- `backend/modules/listings/services.py`", "- ")
        self.assertIn(
            "List the AI-assisted files", pr_policy.check_ai(make_pr(body=body))[0]
        )
        elsewhere = GOOD_BODY.replace("listings/services.py", "stores/models.py")
        self.assertEqual(len(pr_policy.check_ai(make_pr(body=elsewhere))), 1)

    def test_no_substantial_ai_needs_no_file_list(self):
        body = GOOD_BODY.replace(
            "Below 50% AI-generated", "No substantial AI-generated code"
        ).replace("- `backend/modules/listings/services.py`", "")
        self.assertEqual(pr_policy.check_ai(make_pr(body=body)), [])

    def test_a_listed_directory_matches_its_files(self):
        body = GOOD_BODY.replace(
            "`backend/modules/listings/services.py`", "`backend/modules/listings/`"
        )
        self.assertEqual(pr_policy.check_ai(make_pr(body=body)), [])

    def test_bold_line_style_without_heading_passes(self):
        body = "Closes #648\n\n**AI contribution:** 50% or more AI-generated\n\n- backend/modules/listings/services.py\n"
        self.assertEqual(pr_policy.check_ai(make_pr(body=body)), [])

    def test_body_edited_in_the_web_page_with_crlf_passes(self):
        body = (
            "Closes #648\r\n\r\n## AI contribution\r\nLevel: 50% or more AI-generated\r\n\r\n"
            "AI-assisted files:\r\n- backend/modules/listings/services.py\r\n\r\n"
            "## How it was tested\r\nNo tests: settings only\r\n"
        )
        files = [
            ChangedFile("backend/modules/listings/services.py", "modified", HEADER)
        ]
        self.assertEqual(pr_policy.check_ai(make_pr(body=body, files=files)), [])
        self.assertEqual(pr_policy.check_tests(make_pr(body=body, files=files)), [])

    def test_level_inside_a_comment_does_not_count(self):
        body = "## AI contribution\n<!--\n50% or more AI-generated\n-->\nLevel:\n"
        self.assertIn("Found 0", pr_policy.check_ai(make_pr(body=body))[0])

    def test_level_outside_the_section_does_not_count(self):
        body = "## AI contribution\nLevel:\n\n## Notes\nThe old header said 50% or more AI-generated.\n"
        self.assertIn("Found 0", pr_policy.check_ai(make_pr(body=body))[0])

    def test_section_is_found_by_heading_before_other_mentions(self):
        body = (
            "## What changes\nAdds the AI contribution line to files.\n\n" + GOOD_BODY
        )
        self.assertEqual(pr_policy.check_ai(make_pr(body=body)), [])


class HeaderTests(unittest.TestCase):
    def test_file_without_declaration_is_named(self):
        pr = make_pr(files=[ChangedFile("backend/a.py", "added", "import os\n")])
        errors = pr_policy.check_headers(pr)
        self.assertEqual(len(errors), 1)
        self.assertIn("`backend/a.py`", errors[0])

    def test_declaration_after_shebang_or_in_css_comment_passes(self):
        files = [
            ChangedFile(
                "backend/manage.py",
                "modified",
                "#!/usr/bin/env python\n# AI contribution: 50% or more AI-generated\n",
            ),
            ChangedFile(
                "frontend/src/app.css",
                "added",
                "/* AI contribution: No substantial AI-generated code */\n",
            ),
        ]
        self.assertEqual(pr_policy.check_headers(make_pr(files=files)), [])

    def test_declaration_below_line_ten_fails(self):
        text = "\n" * 10 + "# AI contribution: 50% or more AI-generated\n"
        self.assertEqual(
            len(
                pr_policy.check_headers(
                    make_pr(files=[ChangedFile("backend/a.py", "added", text)])
                )
            ),
            1,
        )

    def test_empty_removed_and_exempt_files_are_skipped(self):
        files = [
            ChangedFile("backend/modules/x/__init__.py", "added", ""),
            ChangedFile("backend/old.py", "removed", None),
            ChangedFile(
                "backend/modules/x/migrations/0001_initial.py",
                "added",
                "from django.db import migrations\n",
            ),
            ChangedFile(
                "frontend/src/shared/api/generated.d.ts",
                "modified",
                "export type A = 1;\n",
            ),
            ChangedFile("README.md", "modified", "# Iris\n"),
        ]
        self.assertEqual(pr_policy.check_headers(make_pr(files=files)), [])


class ClassificationTests(unittest.TestCase):
    def test_source_files(self):
        for path in (
            "backend/Dockerfile",
            ".githooks/commit-msg",
            ".github/workflows/ci.yml",
            "docker-compose.yml",
            "frontend/src/app/App.tsx",
            "frontend/index.html",
            "tools/mock_notices/tax.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(pr_policy.is_source(path))
        for path in (
            "README.md",
            "frontend/package.json",
            "backend/uv.lock",
            "frontend/pnpm-lock.yaml",
            "backend/modules/a/migrations/0002_x.py",
            "mock-data/notices/truth.csv",
            ".github/pull_request_template.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(pr_policy.is_source(path))

    def test_test_files(self):
        for path in (
            "backend/tests/test_seed.py",
            "backend/modules/a/tests/factories.py",
            "frontend/src/app/App.test.tsx",
            "frontend/src/test/i18n.test.ts",
            "frontend/scripts/usability/runs.test.mjs",
            ".github/scripts/test_pr_policy.py",
            "backend/conftest.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(pr_policy.is_test(path))
        self.assertFalse(pr_policy.is_test("backend/modules/listings/services.py"))

    def test_code_that_needs_tests(self):
        self.assertTrue(pr_policy.needs_tests("backend/modules/listings/services.py"))
        self.assertTrue(pr_policy.needs_tests(".github/scripts/pr_policy.py"))
        for path in (
            "frontend/vite.config.ts",
            "backend/modules/a/migrations/0001.py",
            "docs/guide.md",
            "frontend/src/app/App.test.tsx",
            "frontend/src/shared/api/generated.d.ts",
        ):
            with self.subTest(path=path):
                self.assertFalse(pr_policy.needs_tests(path))


class TestChangeTests(unittest.TestCase):
    def test_code_without_a_test_change_fails(self):
        files = [
            ChangedFile("backend/modules/listings/services.py", "modified", HEADER)
        ]
        errors = pr_policy.check_tests(make_pr(files=files))
        self.assertEqual(len(errors), 1)
        self.assertIn("`backend/modules/listings/services.py`", errors[0])

    def test_no_tests_line_forms(self):
        for line in (
            "No tests: documentation only",
            "- No tests: documentation only",
            "**No tests:** documentation only",
            "  * no tests: settings only",
        ):
            with self.subTest(line=line):
                self.assertTrue(pr_policy.explains_missing_tests(f"Intro\n{line}\n"))
        for line in (
            "No tests:",
            "No tests:   ",
            "Tests: none",
            "We added No tests: here",
        ):
            with self.subTest(line=line):
                self.assertFalse(pr_policy.explains_missing_tests(f"Intro\n{line}\n"))

    def test_no_tests_line_explains_it(self):
        files = [ChangedFile("backend/iris/settings/base.py", "modified", HEADER)]
        body = (
            GOOD_BODY + "\nNo tests: settings only, covered by the existing checks.\n"
        )
        self.assertEqual(pr_policy.check_tests(make_pr(files=files, body=body)), [])

    def test_no_tests_line_inside_a_comment_does_not_count(self):
        files = [ChangedFile("backend/iris/settings/base.py", "modified", HEADER)]
        body = GOOD_BODY + "\n<!--\nNo tests: documentation only\n-->\n"
        self.assertEqual(len(pr_policy.check_tests(make_pr(files=files, body=body))), 1)

    def test_deleting_code_or_changing_docs_needs_no_test(self):
        files = [
            ChangedFile("backend/modules/audit/tasks.py", "removed"),
            ChangedFile("docs/a.md", "modified", "x"),
        ]
        self.assertEqual(pr_policy.check_tests(make_pr(files=files)), [])


class EvaluateTests(unittest.TestCase):
    def test_compliant_pull_request_passes(self):
        self.assertEqual(pr_policy.evaluate(make_pr()), [])

    def test_every_problem_is_reported_at_once(self):
        pr = make_pr(
            title="Fix stuff",
            closing=[],
            body="",
            files=[ChangedFile("backend/a.py", "added", "x = 1\n")],
        )
        self.assertEqual(len(pr_policy.evaluate(pr)), 5)

    def test_dependency_bot_is_exempt(self):
        pr = make_pr(author="dependabot[bot]", title="Bump pillow", closing=[], body="")
        self.assertEqual(pr_policy.evaluate(pr), [])


class MainTests(unittest.TestCase):
    def test_api_failure_is_reported_without_a_traceback(self):
        def failing_load(*_args):
            raise OSError("certificate verify failed")

        original, pr_policy.load = pr_policy.load, failing_load
        try:
            with (
                unittest.mock.patch.dict("os.environ", {"GITHUB_TOKEN": "t"}),
                unittest.mock.patch("builtins.print") as printed,
            ):
                code = pr_policy.main(["--repo", "o/r", "--pr", "7"])
        finally:
            pr_policy.load = original
        self.assertEqual(code, 2)
        message = printed.call_args.args[0]
        self.assertTrue(
            message.startswith(
                "::error title=PR policy::Could not read pull request #7"
            )
        )
        self.assertEqual(
            message,
            "::error title=PR policy::Could not read pull request #7 from GitHub. "
            "Re-run the check.",
        )
        self.assertNotIn("certificate", message)
        diagnostic = printed.call_args_list[0].args[0]
        self.assertIn("OSError", diagnostic)
        self.assertNotIn("certificate", diagnostic)

    def test_missing_token_is_a_configuration_error(self):
        with (
            unittest.mock.patch.dict("os.environ", {}, clear=True),
            unittest.mock.patch("builtins.print"),
        ):
            self.assertEqual(pr_policy.main(["--repo", "o/r", "--pr", "7"]), 2)


class AnnotationTests(unittest.TestCase):
    def test_reserved_characters_are_escaped(self):
        self.assertEqual(
            pr_policy.annotation("50% done\nnext"),
            "::error title=PR policy::50%25 done%0Anext",
        )


if __name__ == "__main__":
    unittest.main()
