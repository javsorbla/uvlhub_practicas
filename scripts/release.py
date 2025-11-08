import os
import subprocess
import re
import requests
from packaging import version  # Para parsear y comparar versiones semánticas

# === CONFIG ===
REPO = os.getenv("GITHUB_REPOSITORY")  # Obtiene "usuario/repositorio" desde workflow
TOKEN = os.getenv("GITHUB_TOKEN")      # Token para autenticación con la API
HEADERS = {"Authorization": f"token {TOKEN}"}
API_URL = f"https://api.github.com/repos/{REPO}"


def run(command):
    """Ejecuta un comando de shell y devuelve su salida como texto"""
    return subprocess.check_output(command, shell=True, text=True).strip()


def get_latest_tag():
    """Obtiene el último tag semántico del repositorio; si no hay, devuelve '0.0.0'"""
    try:
        return run("git describe --tags $(git rev-list --tags --max-count=1)")
    except subprocess.CalledProcessError:
        return "0.0.0"


def get_commits_since(tag):
    """Devuelve todos los mensajes de commit desde el tag dado"""
    return run(f"git log {tag}..HEAD --pretty=format:%s").splitlines()


def bump_version(base_version, commits):
    """
    Calcula la nueva versión según reglas semánticas:
    - feat! / build! → major
    - feat / build → minor
    - fix / chore → patch
    Solo se aplica el **mayor impacto entre todos los commits**.
    """
    base = version.parse(base_version)
    major, minor, patch = base.release

    level = 0  # 0=patch, 1=minor, 2=major

    for msg in commits:
        if re.match(r"^(fix|chore)", msg):
            level = max(level, 0)
        elif re.match(r"^(feat|build)", msg):
            level = max(level, 1)
        elif re.match(r"^(feat!|build!)", msg):
            level = max(level, 2)

    if level == 2:  # major
        major += 1
        minor = 0
        patch = 0
    elif level == 1:  # minor
        minor += 1
        patch = 0
    elif level == 0 and commits:  # patch
        patch += 1

    return f"{major}.{minor}.{patch}"


def generate_changelog(commits):
    """
    Agrupa los commits en secciones según prefijo y genera un changelog en texto.
    Se eliminan los prefijos de los mensajes en la sección final.
    """
    sections = {
        "Features": [],
        "Fixes": [],
        "Build/Chores": [],
        "Others": []
    }

    for msg in commits:
        # Quita prefijo tipo "feat: mensaje" o "fix: mensaje"
        clean = re.sub(r"^[^:]*:\s*", "", msg)

        if msg.startswith("feat"):
            sections["Features"].append(clean)
        elif msg.startswith("fix"):
            sections["Fixes"].append(clean)
        elif msg.startswith("build") or msg.startswith("chore"):
            sections["Build/Chores"].append(clean)
        else:
            sections["Others"].append(clean)

    # Construye el texto final del changelog
    changelog = ""
    for title, items in sections.items():
        if items:
            changelog += f"## {title}\n" + "\n".join(f"- {i}" for i in items) + "\n\n"

    return changelog.strip()


def create_release(tag, changelog):
    """
    Crea la release en GitHub usando la API REST.
    - tag_name: versión
    - name: título de la release
    - body: changelog generado
    """
    data = {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": changelog or "No changes recorded.",
        "draft": False,
        "prerelease": False
    }
    r = requests.post(f"{API_URL}/releases", headers=HEADERS, json=data)
    if r.status_code != 201:
        print("Error creating release:", r.status_code, r.text)
        raise SystemExit(1)
    print("Release created successfully!")


def main():
    print("Fetching tags and commits...")
    subprocess.run("git fetch --tags", shell=True)  # Asegura tener todos los tags

    last_tag = get_latest_tag()      # Última versión publicada
    commits = get_commits_since(last_tag)  # Commits desde esa versión

    if not commits:
        print("No new commits since last release")
        return

    new_version = bump_version(last_tag, commits)  # Calcula nueva versión
    changelog = generate_changelog(commits)       # Genera changelog agrupado

    print(f"Creating release {new_version}")
    print(f"Changelog:\n{changelog}\n")

    create_release(new_version, changelog)  # Publica la release en GitHub


if __name__ == "__main__":
    main()
