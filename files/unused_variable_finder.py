import subprocess
import os
import re

output_dir = r"C:\Users\David\Desktop"
output_file = os.path.join(output_dir, "glualint_unused_variables.txt")

folders = [
    r"E:\GMOD\Server\garrysmod\gamemodes\metrorp",
    r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode"
]

pattern = re.compile(r"^(.*?):.*line (\d+),.*Unused variable: (\w+)")

with open(output_file, "w", encoding="utf-8") as f:
    for folder in folders:
        try:
            result = subprocess.run(
                ["glualint", folder],
                capture_output=True,
                text=True,
                check=False
            )
            filtered = []
            for line in result.stdout.splitlines():
                match = pattern.search(line)
                if match:
                    path, line_no, var = match.groups()
                    filtered.append(f"{path}, {line_no}, {var}")
            if filtered:
                f.write(f"Results for {folder}:\n")
                f.write("\n".join(filtered))
                f.write("\n\n")
        except Exception as e:
            f.write(f"Error running glualint on {folder}: {e}\n\n")