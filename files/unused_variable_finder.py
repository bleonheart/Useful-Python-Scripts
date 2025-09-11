import subprocess
import os
import re
import sys

output_dir = r"C:\Users\David\Desktop"
output_file = os.path.join(output_dir, "glualint_unused_variables.txt")

folders = [
    r"E:\GMOD\Server\garrysmod\gamemodes\metrorp",
    r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode"
]

os.makedirs(output_dir, exist_ok=True)
pattern = re.compile(
    r"line (\d+).*Unused (variable|argument|loop(?:\s+variable)?)\s*:?\s*['\"]?([A-Za-z_]\w*)['\"]?",
    re.I
)

with open(output_file, "w", encoding="utf-8") as f:
    for folder in folders:
        try:
            result = subprocess.run(
                ["glualint", folder],
                capture_output=True,
                text=True,
                check=False
            )
        except Exception as e:
            print(f"Error running glualint on {folder}: {e}", file=sys.stderr)
            continue
        logs = ((result.stdout or "") + "\n" + (result.stderr or "")).strip("\n")
        for line in logs.splitlines():
            i = line.rfind(": [")
            if i == -1:
                continue
            path = line[:i]
            m = pattern.search(line[i + 2:])
            if not m:
                continue
            issue_type = f"Unused {m.group(2).capitalize()}"
            f.write(f"{path} | {issue_type} | {m.group(1)}, {m.group(3)}\n")