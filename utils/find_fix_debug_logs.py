import os
import re

PROJECT_ROOT = "."  # Adjust to your project root folder path if needed

# Patterns to detect suspicious logging calls:
patterns = [
    re.compile(r'(log_message|backend_log_message)\s*\(\s*[^,]*,\s*[\'"]debug[\'"]\s*,\s*level\s*=\s*[\'"]info[\'"]\s*\)'),
    re.compile(r'(log_message|backend_log_message)\s*\(\s*[^,]*,\s*[\'"]debug[\'"]\s*\)'),  # without explicit level
    re.compile(r'logger\.info\s*\(\s*[\'"]debug[\'"]\s*\)'),
]

def find_debug_info_logs(root):
    results = []
    for subdir, _, files in os.walk(root):
        for file in files:
            if not file.endswith(".py"):
                continue
            filepath = os.path.join(subdir, file)

            # Skip scanning this script file itself to avoid self-reporting
            if os.path.abspath(filepath) == os.path.abspath(__file__):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                line_strip = line.strip()
                for pattern in patterns:
                    if pattern.search(line_strip):
                        results.append((filepath, i+1, line_strip))
    return results

def main():
    matches = find_debug_info_logs(PROJECT_ROOT)
    if not matches:
        print("No suspicious 'debug' logged as 'info' found.")
        return

    print("Found suspicious log calls logging 'debug' at info level:")
    for filepath, lineno, line in matches:
        print(f"{filepath}:{lineno}: {line}")

    # Uncomment below to enable automatic fix (use with caution)
    # for filepath, lineno, line in matches:
    #     with open(filepath, "r", encoding="utf-8") as f:
    #         lines = f.readlines()
    #     original_line = lines[lineno - 1]
    #     # Replace "debug" string literal with more meaningful message or adjust level to debug
    #     fixed_line = re.sub(r'([\'"])debug([\'"])', r'\1DEBUG MESSAGE (fix me)\2', original_line)
    #     fixed_line = re.sub(r'level\s*=\s*[\'"]info[\'"]', 'level="debug"', fixed_line)
    #     lines[lineno - 1] = fixed_line
    #     with open(filepath, "w", encoding="utf-8") as f:
    #         f.writelines(lines)
    #     print(f"Fixed {filepath}:{lineno}")

if __name__ == "__main__":
    main()
