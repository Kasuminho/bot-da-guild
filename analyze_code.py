import subprocess
from pathlib import Path

# Pastas que serão analisadas
TARGET_DIRS = [
    Path("."),          # raiz
    Path("cogs"),
    Path("views"),
    Path("utils"),
]

def collect_py_files():
    files = set()
    for base in TARGET_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if "venv" in p.parts or "__pycache__" in p.parts:
                continue
            files.add(str(p))
    return sorted(files)

FILES = collect_py_files()

def run(title, cmd):
    print("\n" + "=" * 70)
    print(f"🔎 {title}")
    print("=" * 70)
    subprocess.run(cmd, shell=True)

# --------------------------------
# COMPLEXIDADE CICLOMÁTICA
# --------------------------------
run(
    "Complexidade Ciclomática (Radon)",
    "radon cc " + " ".join(FILES) + " -a -nc"
)

# --------------------------------
# MÉTRICAS BRUTAS
# --------------------------------
run(
    "Tamanho / Linhas / Comentários (Radon)",
    "radon raw " + " ".join(FILES)
)

# --------------------------------
# COGNITIVE COMPLEXITY
# --------------------------------
run(
    "Cognitive Complexity (Lizard)",
    "lizard " + " ".join(FILES)
)

# --------------------------------
# QUALIDADE GERAL
# --------------------------------
run(
    "Qualidade Geral (Pylint)",
    "pylint " + " ".join(FILES)
)

# --------------------------------
# ACOPLAMENTO
# --------------------------------
run(
    "Dependências / Acoplamento (PyDeps)",
    "pydeps " + " ".join(FILES)
)
