import argparse
import json
import re
from pathlib import Path


def _yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def set_user_yaml_token(user_yaml_path: Path, kuro_token: str) -> None:
    if not user_yaml_path.exists():
        raise FileNotFoundError(f"Missing {user_yaml_path}")

    content = user_yaml_path.read_text(encoding="utf-8")
    lines = content.splitlines(True)

    token_line_re = re.compile(r"^(?P<indent>\s*)token\s*:\s*(?P<rest>.*?)(?P<nl>\r?\n)?$", re.IGNORECASE)
    replaced = False

    for i, line in enumerate(lines):
        m = token_line_re.match(line)
        if not m:
            continue
        indent = m.group("indent")
        nl = m.group("nl") or "\n"
        lines[i] = f"{indent}token: {_yaml_quote(kuro_token)}{nl}"
        replaced = True
        break

    if not replaced:
        insert_at = 0
        enable_line_re = re.compile(r"^\s*enable\s*:\s*.*", re.IGNORECASE)
        for i, line in enumerate(lines[:20]):
            if enable_line_re.match(line):
                insert_at = i + 1
                break
        nl = "\n"
        lines.insert(insert_at, f"token: {_yaml_quote(kuro_token)}{nl}")

    user_yaml_path.write_text("".join(lines), encoding="utf-8")


def set_ini_bark_token(push_ini_path: Path, bark_token: str) -> None:
    if not push_ini_path.exists():
        raise FileNotFoundError(f"Missing {push_ini_path}")

    content = push_ini_path.read_text(encoding="utf-8")
    lines = content.splitlines(True)

    section_re = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*(?P<nl>\r?\n)?$")
    token_kv_re = re.compile(r"^(?P<indent>\s*)token\s*(?P<sep>[=:])\s*(?P<val>.*?)(?P<nl>\r?\n)?$", re.IGNORECASE)

    in_bark = False
    bark_section_found = False
    token_set = False
    last_bark_line_index = None

    for i, line in enumerate(lines):
        sec = section_re.match(line)
        if sec:
            if in_bark and not token_set:
                lines.insert(i, f"token={bark_token}\n")
                token_set = True
                return

            section_name = sec.group("name").strip().lower()
            in_bark = section_name == "bark"
            if in_bark:
                bark_section_found = True
            continue

        if in_bark:
            last_bark_line_index = i
            m = token_kv_re.match(line)
            if m:
                indent = m.group("indent")
                nl = m.group("nl") or "\n"
                lines[i] = f"{indent}token={bark_token}{nl}"
                token_set = True
                break

    if bark_section_found and not token_set:
        insert_at = (last_bark_line_index + 1) if last_bark_line_index is not None else len(lines)
        lines.insert(insert_at, f"token={bark_token}\n")
        token_set = True

    if not bark_section_found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        if lines and lines[-1].strip() != "":
            lines.append("\n")
        lines.append("[bark]\n")
        lines.append("api_url=https://api.day.app\n")
        lines.append(f"token={bark_token}\n")

    push_ini_path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit Kuro-autosignin config files from CI secrets.")
    parser.add_argument("--kuro-token", required=True, help="Token to write into config/user.yaml -> token")
    parser.add_argument("--bark-token", default="", help="Token to write into config/push.ini -> [bark] token (optional)")
    parser.add_argument("--user-yaml", default="config/user.yaml", help="Path to user.yaml")
    parser.add_argument("--push-ini", default="config/push.ini", help="Path to push.ini")

    args = parser.parse_args()

    set_user_yaml_token(Path(args.user_yaml), args.kuro_token.strip())

    bark_token = (args.bark_token or "").strip()
    if bark_token:
        set_ini_bark_token(Path(args.push_ini), bark_token)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
