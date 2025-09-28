import argparse
import os
import re
import ast
from pathlib import Path
from typing import List, Set

DEFAULT_DIRECTORIES = [
    Path(r"E:\GMOD\Server\garrysmod\gamemodes\metrorp"),
    Path(r"E:\GMOD\Server\garrysmod\gamemodes\lilia"),
]

DEFAULT_IGNORE_FILE = ".commentIgnore"


def _match_long_bracket_opener(text: str, start_index: int):
    i = start_index
    if i >= len(text) or text[i] != "[":
        return False, 0, start_index
    i += 1
    num_equals = 0
    while i < len(text) and text[i] == "=":
        num_equals += 1
        i += 1
    if i < len(text) and text[i] == "[":
        return True, num_equals, i + 1
    return False, 0, start_index


def _find_long_bracket_closer(text: str, start_index: int, num_equals: int):
    closer = "]" + ("=" * num_equals) + "]"
    pos = text.find(closer, start_index)
    return -1 if pos == -1 else pos + len(closer)


def pretty_print_lua(content: str, indent_size: int = 4) -> str:
    """Pretty-print Lua code with consistent indentation and spacing."""
    lines = content.split('\n')
    formatted_lines = []
    indent_level = 0
    prev_line_was_empty = False

    # Keywords that increase indentation
    indent_increase = {'function', 'if', 'for', 'while', 'repeat', 'do', 'then', '{'}
    # Keywords that decrease indentation
    indent_decrease = {'end', 'elseif', 'else', 'until', '}'}
    # Keywords that should be followed by a space
    space_after = {'function', 'if', 'for', 'while', 'repeat', 'until', 'do', 'then', 'elseif', 'else', 'return', 'local'}

    for line in lines:
        original_line = line
        line = line.strip()

        # Skip empty lines but remember we had one
        if not line:
            if not prev_line_was_empty:
                formatted_lines.append('')
            prev_line_was_empty = True
            continue

        prev_line_was_empty = False

        # Remove trailing whitespace
        line = re.sub(r'\s+$', '', line)

        # Add proper spacing around operators
        line = re.sub(r'\s*([=<>!+\-*/%~&|^])\s*', r' \1 ', line)
        line = re.sub(r'\s*([=<>!+\-*/%~&|^])\s*', r' \1 ', line)  # Apply twice for nested operators

        # Ensure space after commas
        line = re.sub(r',(\S)', r', \1', line)

        # Ensure space before opening braces/parentheses in some cases
        line = re.sub(r'(\w)(\()', r'\1 (', line)
        line = re.sub(r'(\w)(\{)', r'\1 \{', line)

        # Handle indentation
        # Count leading keywords that increase/decrease indentation
        words = line.split()
        if words:
            first_word = words[0]

            # Decrease indentation for these keywords (but only if they're at the start)
            if first_word in indent_decrease:
                indent_level = max(0, indent_level - 1)
            elif line.startswith('end') or line.startswith('}'):
                indent_level = max(0, indent_level - 1)
                # Add extra decrease for function ends
                if 'end' in line and ('function' in line or 'if' in line or 'for' in line):
                    pass  # Already decreased above

        # Add indentation
        if line:  # Only indent non-empty lines
            indented_line = ' ' * (indent_level * indent_size) + line
            formatted_lines.append(indented_line)

        # Increase indentation for these keywords
        if words:
            first_word = words[0]
            if first_word in indent_increase:
                indent_level += 1
            elif line.endswith('{'):
                indent_level += 1
            elif 'function' in line and 'end' not in line:
                indent_level += 1

    return '\n'.join(formatted_lines).rstrip() + '\n'


def remove_lua_comments(content: str):
    i = 0
    n = len(content)
    output_chars = []
    lines_removed = 0
    while i < n:
        ch = content[i]
        if ch == "-" and i + 1 < n and content[i + 1] == "-":
            j = i + 2
            if j < n and content[j] == "[":
                is_open, num_eq, end_opener = _match_long_bracket_opener(content, j)
                if is_open:
                    end_idx = _find_long_bracket_closer(content, end_opener, num_eq)
                    if end_idx == -1:
                        lines_removed += content[i:].count("\n")
                        break
                    lines_removed += content[i:end_idx].count("\n")
                    i = end_idx
                    continue
            # For single-line comments, find the end of the line
            comment_start = i
            while i < n and content[i] != "\n":
                i += 1
            # Check if there was any code before the comment on this line
            # Find the start of the current line
            line_start = comment_start
            while line_start > 0 and content[line_start - 1] != "\n":
                line_start -= 1
            # Get the code part (everything before the comment)
            code_part = content[line_start:comment_start].rstrip()
            # If there's actual code before the comment, keep it
            if code_part:
                output_chars.append(code_part)
                # Add newline if we're not at the end
                if i < n and content[i] == "\n":
                    output_chars.append("\n")
                    i += 1
            else:
                # No code before comment, remove the whole line
                lines_removed += 1
                if i < n and content[i] == "\n":
                    output_chars.append("\n")
                    i += 1
            continue
        if ch == '"' or ch == "'":
            quote = ch
            output_chars.append(ch)
            i += 1
            while i < n:
                c = content[i]
                output_chars.append(c)
                i += 1
                if c == "\\":
                    if i < n:
                        output_chars.append(content[i])
                        i += 1
                elif c == quote:
                    break
            continue
        if ch == "[":
            is_open, num_eq, end_opener = _match_long_bracket_opener(content, i)
            if is_open:
                output_chars.append(content[i:end_opener])
                end_idx = _find_long_bracket_closer(content, end_opener, num_eq)
                if end_idx == -1:
                    output_chars.append(content[end_opener:])
                    break
                output_chars.append(content[end_opener:end_idx])
                i = end_idx
                continue
        output_chars.append(ch)
        i += 1
    return "".join(output_chars), lines_removed


def process_file(file_path, dry_run=False, pretty_print=True):
    try:
        # Read as binary first to handle BOM properly
        with open(file_path, "rb") as f:
            raw_data = f.read()

        # Detect encoding and decode
        if raw_data.startswith(b'\xff\xfe'):
            # UTF-16LE BOM
            original_content = raw_data.decode('utf-16le')
        elif raw_data.startswith(b'\xfe\xff'):
            # UTF-16BE BOM
            original_content = raw_data.decode('utf-16be')
        elif raw_data.startswith(b'\xef\xbb\xbf'):
            # UTF-8 BOM
            original_content = raw_data.decode('utf-8-sig')
        else:
            # Try UTF-8 first, then UTF-16LE
            try:
                original_content = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                original_content = raw_data.decode('utf-16le')

        cleaned_content, lines_removed = remove_lua_comments(original_content)

        # Apply pretty-printing if requested
        if pretty_print and original_content != cleaned_content:
            cleaned_content = pretty_print_lua(cleaned_content)

        if original_content != cleaned_content:
            if not dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_content)
                return file_path, lines_removed, True
            else:
                return file_path, lines_removed, False
        else:
            return file_path, 0, False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return file_path, 0, False


def parse_ignore_file(ignore_file_path: Path) -> List[str]:
    """Parse a .luacheckrc-style ignore file and return exclude patterns."""
    if not ignore_file_path.exists():
        return []

    try:
        with open(ignore_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse the Lua table structure
        # Look for exclude_files = { ... } pattern
        exclude_pattern = r'exclude_files\s*=\s*\{([^}]*)\}'
        match = re.search(exclude_pattern, content, re.MULTILINE | re.DOTALL)

        if not match:
            return []

        exclude_content = match.group(1)
        # Extract quoted strings from the exclude content
        patterns = []
        for quote_match in re.finditer(r'["\']([^"\']*)["\']', exclude_content):
            patterns.append(quote_match.group(1))

        return patterns
    except Exception as e:
        print(f"Warning: Could not parse ignore file {ignore_file_path}: {e}")
        return []


def find_ignore_file(directory: Path) -> Path:
    """Find the ignore file in the given directory or its parents."""
    current = directory
    while True:
        ignore_file = current / DEFAULT_IGNORE_FILE
        if ignore_file.exists():
            return ignore_file
        if current.parent == current:
            break
        current = current.parent
    return directory / DEFAULT_IGNORE_FILE


def glob_to_regex(pattern: str) -> str:
    """Convert LuaCheck-style glob pattern to regular expression."""
    # Escape special regex characters except those we handle
    pattern = re.sub(r'([.+^${}()|\[\]\\])', r'\\\1', pattern)

    # Handle ** (matches across path separators)
    pattern = pattern.replace('**', '___DOUBLE_STAR___')

    # Handle * (matches any characters except path separators)
    pattern = pattern.replace('*', '[^/]*')

    # Handle ** back
    pattern = pattern.replace('___DOUBLE_STAR___', '.*')

    # Handle ? (matches any single character except path separators)
    pattern = pattern.replace('?', '[^/]')

    # Handle character classes like [abc] or [!abc]
    pattern = re.sub(r'\\\[([^]]*?)\\\]', r'[\1]', pattern)
    pattern = re.sub(r'\\\[!([^]]*?)\\\]', r'[^/]', pattern)

    # Handle alternatives like {a,b,c}
    pattern = re.sub(r'\\\{([^}]*?)\\\}', r'(?:\1)', pattern)

    return pattern


def should_ignore_file(file_path: Path, ignore_patterns: List[str], base_directory: Path) -> bool:
    """Check if a file should be ignored based on the patterns."""
    if not ignore_patterns:
        return False

    # Convert to relative path from base directory
    try:
        relative_path = file_path.relative_to(base_directory)
        relative_str = str(relative_path).replace('\\', '/')

        for pattern in ignore_patterns:
            # Convert glob pattern to regex
            regex_pattern = glob_to_regex(pattern)
            # Add anchors for full path matching
            regex_pattern = f'^{regex_pattern}$'
            if re.match(regex_pattern, relative_str):
                return True

        return False
    except ValueError:
        # File is not relative to base directory, don't ignore
        return False


def find_lua_files(directory, ignore_patterns=None):
    lua_files = []
    if ignore_patterns is None:
        ignore_patterns = []

    for root, dirs, files in os.walk(directory):
        root_path = Path(root)

        # Filter out ignored directories
        dirs_to_remove = []
        for dir_name in dirs:
            dir_path = root_path / dir_name
            # Check if any ignore pattern matches this directory path
            if should_ignore_file(dir_path, ignore_patterns, directory):
                dirs_to_remove.append(dir_name)
                continue

            # Also check if the directory path matches any pattern
            temp_path = dir_path.relative_to(directory)
            temp_str = str(temp_path).replace('\\', '/')
            for pattern in ignore_patterns:
                regex_pattern = glob_to_regex(pattern)
                # Add anchors for full path matching
                regex_pattern = f'^{regex_pattern}$'
                if re.match(regex_pattern, temp_str):
                    dirs_to_remove.append(dir_name)
                    break

        # Remove ignored directories from traversal
        for dir_name in dirs_to_remove:
            dirs.remove(dir_name)

        for file in files:
            file_path = root_path / file
            if file.endswith(".lua") and not should_ignore_file(file_path, ignore_patterns, directory):
                lua_files.append(file_path)

    return lua_files


def process_file_or_directory(path: Path, dry_run: bool, verbose: bool, pretty_print: bool = True, ignore_patterns: List[str] = None):
    if not path.exists():
        print(f"Error: Path '{path}' does not exist.")
        return 0, 0, 0

    if path.is_file():
        if not path.suffix == ".lua":
            print(f"Error: '{path}' is not a Lua file.")
            return 0, 0, 0
        if verbose:
            print(f"Processing file: {path}")
        _, lines_removed, was_modified = process_file(path, dry_run, pretty_print)
        if lines_removed > 0:
            status = "Would remove" if dry_run else "Removed"
            action = " (with formatting)" if pretty_print and not dry_run else ""
            print(f"{status} {lines_removed} comment lines from {path}{action}")
        return 1, 1 if was_modified else 0, lines_removed
    elif path.is_dir():
        return process_directory(path, dry_run, verbose, pretty_print, ignore_patterns)
    else:
        print(f"Error: '{path}' is neither a file nor a directory.")
        return 0, 0, 0

def process_directory(directory: Path, dry_run: bool, verbose: bool, pretty_print: bool = True, ignore_patterns: List[str] = None):
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist.")
        return 0, 0, 0
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.")
        return 0, 0, 0
    print(f"Searching for Lua files in: {directory.absolute()}")
    lua_files = find_lua_files(directory)
    print(f"Found {len(lua_files)} Lua files")
    if not lua_files:
        return 0, 0, 0
    total_lines_removed = 0
    modified_files = 0
    processed_files = 0
    for file_path in lua_files:
        if verbose:
            print(f"Processing: {file_path}")
        file_path, lines_removed, was_modified = process_file(file_path, dry_run, pretty_print)
        processed_files += 1
        if lines_removed > 0:
            status = "Would remove" if dry_run else "Removed"
            action = " (with formatting)" if pretty_print and not dry_run else ""
            print(f"{status} {lines_removed} comment lines from {file_path}{action}")
            total_lines_removed += lines_removed
            if was_modified:
                modified_files += 1
    return processed_files, modified_files, total_lines_removed


def main():
    parser = argparse.ArgumentParser(
        description="Remove Lua comments from files and format them (formatting enabled by default). "
                   f"Supports {DEFAULT_IGNORE_FILE} files for excluding files and directories."
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="File or directory to process; if omitted, defaults to predefined directories",
    )
    parser.add_argument(
        "--ignore-file", "-i",
        type=str,
        default=DEFAULT_IGNORE_FILE,
        help=f"Path to ignore file (default: {DEFAULT_IGNORE_FILE}). "
             "If not specified, looks for ignore files in processed directories. "
             "Uses exclude_files table with glob patterns like 'documentation/**/*'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--no-pretty-print", "-np",
        action="store_true",
        help="Disable code formatting (comments will still be removed)"
    )
    args = parser.parse_args()

    if args.path:
        dirs_to_process = [Path(args.path)]
    else:
        dirs_to_process = DEFAULT_DIRECTORIES
    grand_total_lines = 0
    grand_modified_files = 0
    grand_processed_files = 0

    # Parse ignore file - if not specified, look for it in each directory
    ignore_patterns = []
    if args.ignore_file != DEFAULT_IGNORE_FILE:
        # Specific ignore file was provided
        ignore_file_path = Path(args.ignore_file)
        ignore_patterns = parse_ignore_file(ignore_file_path)
        if args.verbose and ignore_patterns:
            print(f"Loaded {len(ignore_patterns)} ignore patterns from {ignore_file_path}")
            for pattern in ignore_patterns:
                print(f"  - {pattern}")
    else:
        # Look for ignore files in each directory being processed
        for path in dirs_to_process:
            if path.is_dir():
                ignore_file_path = find_ignore_file(path)
                if ignore_file_path.exists():
                    dir_patterns = parse_ignore_file(ignore_file_path)
                    ignore_patterns.extend(dir_patterns)

        if args.verbose and ignore_patterns:
            print(f"Loaded {len(ignore_patterns)} ignore patterns from found ignore files")
            for pattern in ignore_patterns:
                print(f"  - {pattern}")

    for path in dirs_to_process:
        processed_files, modified_files, total_lines_removed = process_file_or_directory(
            path, args.dry_run, args.verbose, not args.no_pretty_print, ignore_patterns
        )
        grand_processed_files += processed_files
        grand_modified_files += modified_files
        grand_total_lines += total_lines_removed
    if args.dry_run:
        action = " and format" if not args.no_pretty_print else ""
        if len(dirs_to_process) == 1:
            if dirs_to_process[0].is_file():
                print(
                    f"\nDry run complete. Would remove {grand_total_lines} comment lines{action} from 1 file."
                )
            else:
                print(
                    f"\nDry run complete. Would remove {grand_total_lines} comment lines{action} from {grand_modified_files} files across 1 directory."
                )
        else:
            print(
                f"\nDry run complete. Would remove {grand_total_lines} comment lines{action} from {grand_modified_files} files across {len(dirs_to_process)} director{'y' if len(dirs_to_process)==1 else 'ies'}."
            )
    else:
        action = " and formatted" if not args.no_pretty_print else ""
        if len(dirs_to_process) == 1:
            if dirs_to_process[0].is_file():
                print(
                    f"\nComplete! Removed {grand_total_lines} comment lines{action} from 1 file."
                )
            else:
                print(
                    f"\nComplete! Removed {grand_total_lines} comment lines{action} from {grand_modified_files} files across 1 directory."
                )
        else:
            print(
                f"\nComplete! Removed {grand_total_lines} comment lines{action} from {grand_modified_files} files across {len(dirs_to_process)} director{'y' if len(dirs_to_process)==1 else 'ies'}."
            )


if __name__ == "__main__":
    main()