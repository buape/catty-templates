#!/usr/bin/env python3
"""Submit one GitHub PR review with batched inline comments."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def run_gh(args: list[str]) -> str:
	env = os.environ.copy()
	env.setdefault("GH_CONFIG_DIR", str(Path.home() / ".config" / "gh"))
	result = subprocess.run(
		["gh", *args],
		check=False,
		text=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		env=env,
	)
	if result.returncode != 0:
		if result.stdout:
			print(result.stdout, file=sys.stderr)
		if result.stderr:
			print(result.stderr, file=sys.stderr)
		raise SystemExit(result.returncode)
	return result.stdout


def gh_json(args: list[str]) -> Any:
	output = run_gh(args)
	try:
		return json.loads(output)
	except json.JSONDecodeError as error:
		print(output, file=sys.stderr)
		raise SystemExit(f"gh did not return JSON: {error}") from error


def infer_repo() -> str:
	return run_gh(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]).strip()


def infer_pr() -> str:
	return run_gh(["pr", "view", "--json", "number", "--jq", ".number"]).strip()


def flatten_pages(data: Any) -> list[dict[str, Any]]:
	if not isinstance(data, list):
		raise SystemExit("Expected a JSON list from GitHub")
	if data and all(isinstance(page, list) for page in data):
		return [item for page in data for item in page]
	if all(isinstance(item, dict) for item in data):
		return data
	raise SystemExit("Unexpected paginated GitHub response shape")


def patch_commentable_lines(patch: str) -> set[tuple[str, int]]:
	lines: set[tuple[str, int]] = set()
	old_line: int | None = None
	new_line: int | None = None

	for raw_line in patch.splitlines():
		match = HUNK_RE.match(raw_line)
		if match:
			old_line = int(match.group(1))
			new_line = int(match.group(3))
			continue

		if old_line is None or new_line is None or raw_line.startswith("\\"):
			continue

		prefix = raw_line[:1]
		if prefix == " ":
			lines.add(("LEFT", old_line))
			lines.add(("RIGHT", new_line))
			old_line += 1
			new_line += 1
		elif prefix == "-":
			lines.add(("LEFT", old_line))
			old_line += 1
		elif prefix == "+":
			lines.add(("RIGHT", new_line))
			new_line += 1

	return lines


def load_pr_patches(repo: str, pr: str) -> dict[str, set[tuple[str, int]]]:
	files = flatten_pages(
		gh_json(["api", f"repos/{repo}/pulls/{pr}/files", "--paginate", "--slurp"])
	)
	patches: dict[str, set[tuple[str, int]]] = {}
	for file in files:
		filename = file.get("filename")
		patch = file.get("patch")
		if isinstance(filename, str) and isinstance(patch, str):
			patches[filename] = patch_commentable_lines(patch)
	return patches


def load_comments(path: Path) -> list[dict[str, Any]]:
	try:
		comments = json.loads(path.read_text())
	except json.JSONDecodeError as error:
		raise SystemExit(f"Invalid comments JSON: {error}") from error
	if not isinstance(comments, list):
		raise SystemExit("Comments file must contain a JSON array")
	for index, comment in enumerate(comments, start=1):
		if not isinstance(comment, dict):
			raise SystemExit(f"Comment {index} must be an object")
		if not isinstance(comment.get("path"), str):
			raise SystemExit(f"Comment {index} is missing string path")
		if not isinstance(comment.get("body"), str) or not comment["body"].strip():
			raise SystemExit(f"Comment {index} is missing non-empty body")
	return comments


def validate_comments(
	comments: list[dict[str, Any]],
	patches: dict[str, set[tuple[str, int]]],
	allow_position: bool,
) -> None:
	for index, comment in enumerate(comments, start=1):
		path = comment["path"]
		if "position" in comment and not allow_position:
			raise SystemExit(
				f"Comment {index} uses position. Use line+side, or pass --allow-position after manually verifying the diff offset."
			)
		if "position" in comment:
			continue

		line = comment.get("line")
		side = comment.get("side")
		if not isinstance(line, int):
			raise SystemExit(f"Comment {index} is missing integer line")
		if side not in {"LEFT", "RIGHT"}:
			raise SystemExit(f"Comment {index} side must be LEFT or RIGHT")
		if path not in patches:
			raise SystemExit(
				f"Comment {index} path {path!r} has no patch in the PR files response. Is the file/line in the PR diff?"
			)
		if (side, line) not in patches[path]:
			raise SystemExit(
				f"Comment {index} targets {path}:{line} {side}, but that line is not commentable in the PR diff"
			)

		start_line = comment.get("start_line")
		if start_line is not None:
			start_side = comment.get("start_side", side)
			if not isinstance(start_line, int):
				raise SystemExit(f"Comment {index} start_line must be an integer")
			if start_side not in {"LEFT", "RIGHT"}:
				raise SystemExit(f"Comment {index} start_side must be LEFT or RIGHT")
			if (start_side, start_line) not in patches[path]:
				raise SystemExit(
					f"Comment {index} start_line targets {path}:{start_line} {start_side}, but that line is not commentable in the PR diff"
				)


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Submit one GitHub PR review with batched inline comments."
	)
	parser.add_argument("--repo", help="OWNER/REPO. Defaults to gh repo view.")
	parser.add_argument("--pr", help="Pull request number. Defaults to gh pr view.")
	parser.add_argument(
		"--event",
		choices=["REQUEST_CHANGES", "APPROVE"],
		default="REQUEST_CHANGES",
	)
	parser.add_argument(
		"--comments-file",
		type=Path,
		help="JSON array of inline comments. Each comment needs path, line, side, body.",
	)
	parser.add_argument(
		"--body-file",
		type=Path,
		help="Top-level review body file.",
	)
	parser.add_argument(
		"--allow-position",
		action="store_true",
		help="Allow legacy position comments after manual diff-offset verification.",
	)
	parser.add_argument(
		"--allow-empty",
		action="store_true",
		help="Allow no inline comments. Intended for APPROVE reviews only.",
	)
	parser.add_argument("--dry-run", action="store_true", help="Print payload only.")
	args = parser.parse_args()

	repo = args.repo or infer_repo()
	pr = args.pr or infer_pr()
	if args.comments_file:
		comments = load_comments(args.comments_file)
	else:
		comments = []
	if not comments and not args.allow_empty:
		raise SystemExit(
			"Refusing to submit a review with no inline comments unless --allow-empty is passed"
		)
	if not comments and args.event != "APPROVE":
		raise SystemExit("Empty reviews are only allowed for APPROVE")
	if args.event == "APPROVE" and comments:
		raise SystemExit("APPROVE reviews must not include inline finding comments")
	if not args.body_file and args.event != "APPROVE":
		raise SystemExit("A top-level review summary is required via --body-file")

	if comments:
		patches = load_pr_patches(repo, pr)
		validate_comments(comments, patches, args.allow_position)

	payload = {
		"event": args.event,
		"comments": comments,
	}
	if args.body_file:
		payload["body"] = args.body_file.read_text()

	if args.dry_run:
		print(json.dumps(payload, indent=2))
		return 0

	with tempfile.NamedTemporaryFile(
		"w", prefix="gh-pr-inline-review-", suffix=".json", delete=False
	) as file:
		json.dump(payload, file)
		payload_path = file.name

	try:
		review = gh_json(
			[
				"api",
				f"repos/{repo}/pulls/{pr}/reviews",
				"--method",
				"POST",
				"--input",
				payload_path,
			]
		)
	finally:
		try:
			os.unlink(payload_path)
		except FileNotFoundError:
			pass

	review_id = review.get("id") if isinstance(review, dict) else None
	print(json.dumps({"review_id": review_id, "state": review.get("state")}, indent=2))

	if review_id is not None:
		all_comments = flatten_pages(
			gh_json(
				[
					"api",
					f"repos/{repo}/pulls/{pr}/comments",
					"--paginate",
					"--slurp",
				]
			)
		)
		created_comments = [
			{
				"id": comment.get("id"),
				"path": comment.get("path"),
				"line": comment.get("line"),
				"side": comment.get("side"),
				"pull_request_review_id": comment.get("pull_request_review_id"),
			}
			for comment in all_comments
			if comment.get("pull_request_review_id") == review_id
		]
		print(json.dumps({"inline_comments": created_comments}, indent=2))

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
