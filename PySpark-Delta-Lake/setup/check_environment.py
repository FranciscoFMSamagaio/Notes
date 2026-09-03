import shutil
import subprocess
import sys


def run(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    return completed.returncode, output


print(f"Python: {sys.version.split()[0]}")

java_path = shutil.which("java")
if java_path is None:
    print("Java: not found")
    print("Install Java 17, then open a new terminal and run this check again.")
else:
    code, output = run(["java", "-version"])
    if code == 0:
        print(f"Java executable: {java_path}")
        print(output)
    else:
        print("Java: command exists, but no runtime is configured")
        print(output)
        print("Install Java 17, then open a new terminal and run this check again.")

try:
    import pyspark

    print(f"PySpark: {pyspark.__version__}")
except ImportError:
    print("PySpark: not installed")
    print("Run: .venv/bin/pip install -r requirements.txt")
