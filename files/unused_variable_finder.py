import subprocess
import os
import re

output_dir = r"C:\Users\David\Desktop"
output_file = os.path.join(output_dir, "glualint_unused_variables.txt")

folders = [
    r"E:\GMOD\Server\garrysmod\gamemodes\metrorp",
    r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode"
]

with open(output_file, "w", encoding="utf-8") as f:
    for folder in folders:
        try:
            result = subprocess.run(
                ["glualint", folder],
                capture_output=True,
                text=True,
                check=False
            )
            for line in result.stdout.splitlines():
                i = line.rfind(": [")
                if i == -1:
                    continue
                path = line[:i]
                m = re.search(r"line (\d+).*Unused variable:\s+([A-Za-z_]\w*)", line[i+2:])
                if not m:
                    continue
                f.write(f"{path}, {m.group(1)}, {m.group(2)}\n")
        except Exception as e:
            f.write(f"Error running glualint on {folder}: {e}\n")