import os

def find_debug_literal_logs():
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    for num, line in enumerate(f, 1):
                        line_strip = line.strip()
                        if (
                            'log_message("debug"' in line_strip or
                            "log_message('debug'" in line_strip or
                            'logger.info("debug"' in line_strip or
                            "logger.info('debug'" in line_strip
                        ):
                            print(f"{path}:{num}: {line_strip}")

if __name__ == "__main__":
    find_debug_literal_logs()
