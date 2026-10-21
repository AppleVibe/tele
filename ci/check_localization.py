#!/usr/bin/env python3
"""Static localization/publication audit; not a complete UI coverage check.

Only literal templates passed to explicit translation APIs are coverage-checked.
Dynamic expressions, macros, runtime language selection and UI layout need review.
No private keys or credentials are read. OpenSSL checks public-key DER only.
"""
import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int


_SIMPLE_ESCAPES = dict(zip("abfnrtv\\\"'?", "\a\b\f\n\r\t\v\\\"'?"))
_LITERAL = re.compile(r'(?:u8|u|U|L)?(?:R)?"')
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_PLACEHOLDER = re.compile(r"%%|%L(?:[1-9][0-9]?|n)|%[1-9][0-9]?|%n")


def placeholders(text):
    """Preserve spelling AND multiplicity; %% is a distinct token."""
    return Counter(_PLACEHOLDER.findall(text))


def lex(source):
    """C++ tokens with decoded strings; comments/chars cannot become API calls.

    Supports ordinary/prefixed/raw strings, UDL suffixes, adjacent literals,
    standard escapes, octal/hex escapes and physical line continuations.
    Lexical errors are returned, not thrown (also for hostile/fuzz input).
    """
    tokens, errors = [], []
    i, line, size = 0, 1, len(source)
    while i < size:
        char = source[i]
        if source.startswith("\\\r\n", i) or source.startswith("\\\n", i):
            i += 3 if source.startswith("\\\r\n", i) else 2
            line += 1
            continue
        if char.isspace():
            line += char == "\n"
            i += 1
            continue
        if source.startswith("//", i):
            i += 2
            while i < size:
                if source.startswith("\\\n", i) or source.startswith("\\\r\n", i):
                    i += 3 if source.startswith("\\\r\n", i) else 2
                    line += 1
                elif source[i] == "\n":
                    break
                else:
                    i += 1
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            if end < 0:
                errors.append((line, "unterminated comment"))
                break
            line += source[i:end + 2].count("\n")
            i = end + 2
            continue
        start_line = line
        match = _LITERAL.match(source, i)
        if match:
            raw = "R" in match.group()
            i = match.end()
            value = []
            if raw:
                opening = source.find("(", i, i + 17)
                delimiter = source[i:opening] if opening >= 0 else ""
                if opening < 0 or re.search(r'[\s()\\]', delimiter):
                    errors.append((line, "invalid raw-string delimiter"))
                    continue
                closing = source.find(")" + delimiter + '"', opening + 1)
                if closing < 0:
                    errors.append((line, "unterminated raw string"))
                    break
                value.append(source[opening + 1:closing])
                line += source[i:closing + len(delimiter) + 2].count("\n")
                i = closing + len(delimiter) + 2
            else:
                closed = False
                while i < size:
                    char = source[i]
                    i += 1
                    if char == '"':
                        closed = True
                        break
                    if char == "\n":
                        errors.append((line, "unescaped newline in string"))
                        line += 1
                    if char != "\\":
                        value.append(char)
                        continue
                    if i >= size:
                        break
                    escape = source[i]
                    i += 1
                    if escape == "\n" or (escape == "\r" and source[i:i + 1] == "\n"):
                        i += escape == "\r"
                        line += 1
                    elif escape in _SIMPLE_ESCAPES:
                        value.append(_SIMPLE_ESCAPES[escape])
                    elif escape in "uUx":
                        width = {"u": 4, "U": 8}.get(escape)
                        digits = re.match(r"[0-9a-fA-F]+", source[i:])
                        digits = digits.group() if digits else ""
                        digits = digits[:width] if width else digits
                        i += len(digits)
                        if not digits or (width and len(digits) != width):
                            errors.append((start_line, "malformed Unicode/hex escape"))
                            value.append("\ufffd")
                        else:
                            number = int(digits, 16)
                            if number > 0x10ffff:
                                errors.append((start_line, "out-of-range Unicode/hex escape"))
                                value.append("\ufffd")
                            else:
                                value.append(chr(number))
                    elif escape in "01234567":
                        digits = escape
                        while i < size and len(digits) < 3 and source[i] in "01234567":
                            digits += source[i]
                            i += 1
                        value.append(chr(int(digits, 8)))
                    else:
                        errors.append((start_line, "unknown escape \\" + escape))
                        value.append(escape)
                if not closed:
                    errors.append((start_line, "unterminated string"))
            # A UDL suffix belongs to the literal, including the usual _q.
            suffix = _IDENTIFIER.match(source, i)
            if suffix:
                i = suffix.end()
            decoded = "".join(value)
            # Qt UTF-16 literals can express non-BMP characters as surrogate pairs.
            decoded = decoded.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "surrogatepass")
            tokens.append(Token("string", decoded, start_line))
            continue
        # Numeric separators (1'000) are not character constants.
        if char.isdigit() or (char == "." and i + 1 < size and source[i + 1].isdigit()):
            end = i + 1
            while end < size:
                current = source[end]
                if current.isalnum() or current in "_'.":
                    end += 1
                elif current in "+-" and source[end - 1] in "eEpP":
                    end += 1
                else:
                    break
            tokens.append(Token("number", source[i:end], line))
            i = end
            continue
        # Ignore character constants, including prefixed ones, before identifiers.
        character = re.match(r"(?:u8|u|U|L)?'", source[i:])
        if character:
            i += character.end()
            closed = False
            while i < size:
                char = source[i]
                i += 1
                if char == "\\" and i < size:
                    line += source[i] == "\n"
                    i += 1
                elif char == "'":
                    closed = True
                    break
                else:
                    line += char == "\n"
            if not closed:
                errors.append((start_line, "unterminated character literal"))
            continue
        match = _IDENTIFIER.match(source, i)
        if match:
            tokens.append(Token("identifier", match.group(), line))
            i = match.end()
        elif source.startswith("::", i):
            tokens.append(Token("punctuation", "::", line))
            i += 2
        else:
            tokens.append(Token("punctuation", char, line))
            i += 1
    return tokens, errors


def closing(tokens, start):
    pairs = {"(": ")", "{": "}", "[": "]"}
    stack = []
    for i in range(start, len(tokens)):
        value = tokens[i].value
        if tokens[i].kind == "string":
            continue
        if value in pairs:
            stack.append(pairs[value])
        elif value in pairs.values():
            if not stack or stack.pop() != value:
                return None
            if not stack:
                return i
    return None


def arguments(tokens):
    result, start, stack = [], 0, []
    for i, token in enumerate(tokens):
        if token.kind == "string":
            continue
        if token.value in ("(", "{", "["):
            stack.append(token.value)
        elif token.value in (")", "}", "]") and stack:
            stack.pop()
        elif token.value == "," and not stack:
            result.append(tokens[start:i])
            start = i + 1
    result.append(tokens[start:])
    return result


def literal(tokens):
    """Only whole literal expressions, optionally QString/View-wrapped."""
    if not any(token.kind == "string" for token in tokens) and [token.value for token in tokens] in (["{", "}"], ["QStringView", "{", "}"], ["QStringView", "(", ")"]):
        return ""
    while tokens:
        offset = 1 if tokens[0].value == "(" else 2
        wrapped = tokens[0].value == "(" or (
            len(tokens) > 2 and tokens[0].value in ("QStringView", "QString", "QLatin1String")
            and tokens[1].value == "(")
        if not wrapped or closing(tokens, offset - 1) != len(tokens) - 1:
            break
        tokens = tokens[offset:-1]
    if tokens and all(token.kind == "string" for token in tokens):
        return "".join(token.value for token in tokens)
    return None


def suspicious(text):
    reasons = []
    if "\ufffd" in text or any(0xd800 <= ord(c) <= 0xdfff for c in text):
        reasons.append("replacement character or unpaired Unicode surrogate")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in text):
        reasons.append("unexpected control character")
    # Advisory only: legitimate multilingual text can resemble damaged UTF-8.
    if re.search(r"(?:[ÐÑ][\u0080-\u00bf]){2}|(?:[РС][\u0400-\u045f]){3}|Ã.|Â[\u0080-\u00bf]|â[\u0080-\u00bf]", text):
        reasons.append("possible mixed/UTF-8 mojibake (manual review)")
    return reasons


def catalog_entries(tokens):
    start = next((i for i, t in enumerate(tokens) if t.value == "kEntries"), None)
    if start is None:
        return [], [(1, "kEntries catalog not found")]
    start = next((i for i in range(start, len(tokens)) if tokens[i].value == "{"), None)
    end = closing(tokens, start) if start is not None else None
    if start is None or end is None:
        return [], [(1, "unbalanced catalog initializer")]
    entries, errors = [], []
    for row in arguments(tokens[start + 1:end]):
        if not row:
            continue
        if row[0].value != "{" or closing(row, 0) != len(row) - 1:
            errors.append((row[0].line, "unsupported catalog row"))
            continue
        fields = arguments(row[1:-1])
        values = [literal(field) for field in fields]
        if len(values) not in (2, 3) or any(value is None for value in values):
            errors.append((row[0].line, "catalog row must contain literal source/translation[/context]"))
            continue
        entries.append((values[0], values[1], values[2] if len(values) == 3 else "", row[0].line))
    if not entries:
        errors.append((tokens[start].line, "catalog contains no parsed entries"))
    return entries, errors


def explicit_calls(tokens):
    """Qualified APIs only; no global raw-English heuristic."""
    for i, token in enumerate(tokens):
        if token.kind != "identifier" or token.value not in ("Text", "Translate", "Plural"):
            continue
        if i < 2 or tokens[i - 1].value != "::" or tokens[i - 2].value not in ("I18n", "Tele"):
            continue
        if i + 1 >= len(tokens) or tokens[i + 1].value != "(":
            continue
        end = closing(tokens, i + 1)
        if end is not None:
            yield token.value, token.line, arguments(tokens[i + 2:end])


def call_findings(tokens, keys):
    findings, static, dynamic = [], 0, 0
    for api, line, args in explicit_calls(tokens):
        if api == "Plural":
            if len(args) != 6:
                findings.append(("error", line, "plural-arity", "Plural requires count and five literal templates"))
                continue
            forms = [literal(arg) for arg in args[1:]]
            if any(form is None for form in forms):
                dynamic += 1
                continue
            forms = [form for form in forms if form is not None]
            static += 1
            if any(not form.strip() for form in forms):
                findings.append(("error", line, "empty-translation", "empty plural template"))
            if any(placeholders(form) != placeholders(forms[0]) for form in forms[1:]):
                findings.append(("error", line, "placeholder-multiset", "plural templates have different placeholder multisets"))
            for form in forms:
                for reason in suspicious(form):
                    findings.append(("warning", line, "suspicious-text", reason + ": " + repr(form)))
            continue
        source = literal(args[0])
        if any(t.kind == "punctuation" and t.value == "." and args[0][i + 1].value == "arg"
               for i, t in enumerate(args[0][:-1])):
            findings.append(("error", line, "formatted-before-translation", "translate template before .arg(...)"))
        if source is None:
            dynamic += 1
            continue
        static += 1
        context = literal(args[1]) if api == "Text" and len(args) > 1 else ""
        if api == "Text" and len(args) > 1 and context is None:
            # A runtime context cannot be checked against static catalog keys.
            dynamic += 1
            static -= 1
            continue
        # Text falls back to the context-free catalog when no override exists.
        if (source, context) not in keys and (source, "") not in keys:
            findings.append(("error", line, "missing-translation", repr((source, context))))
    return findings, static, dynamic


def lower_findings(tokens):
    findings = []
    for i, token in enumerate(tokens[:-1]):
        if token.kind != "identifier" or token.value != "Lower" or tokens[i + 1].value != "(":
            continue
        end = closing(tokens, i + 1)
        if end is None or end + 1 >= len(tokens) or tokens[end + 1].value != "{":
            continue
        body_end = closing(tokens, end + 1)
        if body_end is None:
            continue
        body = tokens[end + 2:body_end]
        if any(t.kind == "identifier" and t.value == "I18n" and j + 2 < len(body)
               and body[j + 1].value == "::" and body[j + 2].value in ("Translate", "Text")
               for j, t in enumerate(body)):
            findings.append(("error", token.line, "lower-translation-hook", "Lower must not perform I18n translation"))
    return findings


def constant(tokens, name):
    for i, token in enumerate(tokens):
        if token.value != name:
            continue
        end = next((j for j in range(i + 1, len(tokens)) if tokens[j].value == ";"), len(tokens))
        equals = next((j for j in range(i + 1, end) if tokens[j].value == "="), None)
        if equals is not None:
            return literal(tokens[equals + 1:end])
    return None


def publication_findings(tdesktop, repo, repository, upstream):
    path = tdesktop / "Telegram/SourceFiles/tele/tele_updater.cpp"
    findings = []
    if not path.is_file():
        return [("error", str(path), 1, "publication", "updater source missing")]
    tokens, errors = lex(path.read_text(encoding="utf-8"))
    for line, message in errors:
        findings.append(("error", str(path), line, "lexer", message))
    expected = {
        "kFeedUrlPrefix": f"https://github.com/{repository}/releases/latest/download/tele-update-",
        "kDownloadPrefix": f"https://github.com/{repository}/releases/download/",
    }
    for name, value in expected.items():
        if constant(tokens, name) != value:
            findings.append(("error", str(path), 1, "publication-url", f"{name} must equal {value!r}"))
    history = tdesktop / "Telegram/SourceFiles/tele/tele_changelog_history.cpp"
    if not history.is_file():
        findings.append(("error", str(history), 1, "publication", "release history source missing"))
    else:
        history_tokens, history_errors = lex(history.read_text(encoding="utf-8"))
        findings.extend(("error", str(history), line, "lexer", message) for line, message in history_errors)
        history_urls = {
            "kListUrl": f"https://api.github.com/repos/{repository}/releases?per_page=30",
            "kReleasesPrefix": f"https://github.com/{repository}/releases/",
            "kRepoPrefix": f"https://github.com/{repository}/",
        }
        for name, value in history_urls.items():
            if constant(history_tokens, name) != value:
                findings.append(("error", str(history), 1, "publication-url", f"{name} must equal {value!r}"))
    pem = repo / "ci/update-public-key.pem"
    try:
        result = subprocess.run(
            ["openssl", "pkey", "-pubin", "-in", str(pem), "-outform", "DER"],
            capture_output=True, check=True, timeout=10,
        )
        # Ed25519 SPKI is exactly this header plus 32 public bytes.
        header = bytes.fromhex("302a300506032b6570032100")
        if len(result.stdout) != len(header) + 32 or not result.stdout.startswith(header):
            raise ValueError("public PEM is not Ed25519 SPKI")
        if constant(tokens, "kPublicKeyHex") != result.stdout[-32:].hex():
            findings.append(("error", str(path), 1, "public-key", "embedded key differs from repository public PEM"))
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        findings.append(("error", str(pem), 1, "public-key", str(error)))
    if upstream is not None:
        pin = repo / "UPSTREAM"
        if not pin.is_file() or pin.read_text(encoding="utf-8").strip() != upstream:
            findings.append(("error", str(pin), 1, "upstream-pin", f"expected unchanged pin {upstream!r}"))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tdesktop", required=True, type=Path)
    parser.add_argument("--repository", default="AppleVibe/tele-ru", help="expected GitHub owner/repo")
    parser.add_argument("--expected-upstream", help="optionally assert exact UPSTREAM pin (e.g. v7.3.1)")
    args = parser.parse_args(argv)
    root = args.tdesktop.resolve()
    repo = Path(__file__).resolve().parent.parent
    catalog = root / "Telegram/SourceFiles/tele/tele_i18n.cpp"
    findings = []
    try:
        tokens, errors = lex(catalog.read_text(encoding="utf-8"))
        entries, parse_errors = catalog_entries(tokens)
        findings.extend(("error", str(catalog), line, "catalog-lexer", message) for line, message in errors + parse_errors)
        keys = set()
        for source, translation, context, line in entries:
            key = (source, context)
            if key in keys:
                findings.append(("error", str(catalog), line, "duplicate-key", repr(key)))
            keys.add(key)
            if not translation.strip():
                findings.append(("error", str(catalog), line, "empty-translation", repr(source)))
            if placeholders(source) != placeholders(translation):
                findings.append(("error", str(catalog), line, "placeholder-multiset", f"{source!r}: {dict(placeholders(source))} != {dict(placeholders(translation))}"))
            for label, value in (("source", source), ("translation", translation), ("context", context)):
                for reason in suspicious(value):
                    findings.append(("warning", str(catalog), line, "suspicious-text", f"{label}: {reason}: {value!r}"))
        static = dynamic = files = 0
        for path in sorted((root / "Telegram/SourceFiles").rglob("*")):
            if path.suffix not in (".cpp", ".h", ".hpp", ".cc", ".mm") or path == catalog:
                continue
            # Regression fixtures intentionally contain untranslated negatives.
            if path.stem.endswith(("_test", "_tests")) or any(part in ("test", "tests") for part in path.relative_to(root / "Telegram/SourceFiles").parts[:-1]):
                continue
            source = path.read_text(encoding="utf-8")
            if not re.search(r"\b(?:I18n|Tele|Lower)\b", source):
                files += 1
                continue
            tokens, errors = lex(source)
            # Report lexer errors only in files relevant to this bounded audit.
            calls, count, skipped = call_findings(tokens, keys)
            lower = lower_findings(tokens)
            if count or skipped or lower:
                findings.extend(("error", str(path), line, "source-lexer", message) for line, message in errors)
            findings.extend((severity, str(path), line, code, message) for severity, line, code, message in calls + lower)
            static += count
            dynamic += skipped
            files += 1
        findings.extend(publication_findings(root, repo, args.repository, args.expected_upstream))
    except (OSError, UnicodeError) as error:
        print(f"ERROR audit-input: {error}", file=sys.stderr)
        return 2
    for severity, path, line, code, message in findings:
        print(f"{severity.upper()} {path}:{line} [{code}] {message}")
    errors = sum(finding[0] == "error" for finding in findings)
    warnings = len(findings) - errors
    print(f"Catalog: {len(entries)} entries; scanned {files} files; explicit literal calls (including Plural): {static}; dynamic calls skipped: {dynamic}.")
    print(f"Result: {errors} errors, {warnings} advisory warnings. Not complete UI coverage; dynamic/macros/runtime behavior require review.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
