"""
Vérifie qu'Obsidian et le vault (wiki/, _meta/, .obsidian/) sont installés/scaffoldés
correctement — structure de dossiers, frontmatter des pages, et résolution des wikilinks
internes (aucun [[lien]] cassé pointant vers une page qui n'existe pas).

Ne teste PAS le contenu applicatif de jarvis-debate (voir les autres tests/test_*.py) —
uniquement l'intégrité du vault de documentation.
"""
import os
import py_compile
import re
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"
META_DIR = PROJECT_ROOT / "_meta"
TEMPLATES_DIR = PROJECT_ROOT / "_templates"
OBSIDIAN_DIR = PROJECT_ROOT / ".obsidian"

# _meta/log.md est un journal append-only (style git-log), pas une "page" de wiki —
# volontairement sans frontmatter YAML.
PAGES_WITHOUT_FRONTMATTER = {META_DIR / "log.md"}

WIKI_SUBFOLDERS = ["modules", "components", "decisions", "dependencies", "flows"]


def _all_vault_pages() -> list[Path]:
    pages: list[Path] = []
    if WIKI_DIR.is_dir():
        pages.extend(WIKI_DIR.rglob("*.md"))
    if META_DIR.is_dir():
        pages.extend(META_DIR.glob("*.md"))
    return pages


def _parse_frontmatter(text: str) -> tuple[bool, str]:
    """Retourne (a_frontmatter, bloc_frontmatter_brut). Parsing volontairement minimal
    (pas de dépendance YAML — cohérent avec la politique 'pas de dépendances inutiles')."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False, ""
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return True, "\n".join(lines[1:i])
    return False, ""


def _extract_wikilinks(text: str) -> set[str]:
    """Extrait les cibles de [[Lien]], [[Lien|Alias]], [[Lien#Section]]."""
    targets = set()
    for raw in re.findall(r"\[\[([^\]]+)\]\]", text):
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if target:
            targets.add(target)
    return targets


def _obsidian_install_dir() -> Path:
    # Emplacement réel constaté après `winget install Obsidian.Obsidian` : sous
    # Programs\, pas directement sous LOCALAPPDATA\Obsidian (qui ne contient que
    # obsidian-updater\) — la doc references/plugins.md du plugin est imprécise
    # sur ce point pour les installs winget.
    return Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Obsidian"


def _obsidian_exe() -> Path:
    return _obsidian_install_dir() / "Obsidian.exe"


def _obsidian_cli() -> Path:
    # Obsidian 1.12+ ships a CLI entry point alongside the GUI exe.
    return _obsidian_install_dir() / "Obsidian.com"


class TestObsidianInstalled(unittest.TestCase):
    """Vérifications statiques (fichiers sur disque) — ne nécessitent pas qu'Obsidian
    soit lancé."""

    def test_obsidian_gui_binary_present(self):
        if os.name != "nt":
            self.skipTest("Vérification d'installation spécifique à Windows (winget).")
        self.assertTrue(
            _obsidian_exe().is_file(),
            f"Obsidian.exe non trouvé sous {_obsidian_exe()} — attendu après "
            f"`winget install Obsidian.Obsidian`.",
        )

    def test_obsidian_cli_binary_present(self):
        if os.name != "nt":
            self.skipTest("Vérification d'installation spécifique à Windows (winget).")
        self.assertTrue(
            _obsidian_cli().is_file(),
            f"Obsidian.com (CLI, Obsidian 1.12+) non trouvé sous {_obsidian_cli()} — "
            f"requis pour le transport 'cli' du plugin claude-obsidian (voir wiki-cli skill).",
        )


class TestObsidianRunning(unittest.TestCase):
    """Vérification dynamique : Obsidian est-il *up et fonctionnel* maintenant (pas
    seulement installé) ? Si l'app n'est pas lancée, on `skip` (ce n'est pas un bug —
    Obsidian n'a pas vocation à tourner en permanence, ex: en CI) plutôt que d'échouer.
    Si l'app tourne, on vérifie que la CLI répond réellement — c'est la seule façon de
    prouver que l'app n'est pas juste un process zombie."""

    def test_cli_responds_when_obsidian_is_running(self):
        if os.name != "nt":
            self.skipTest("Vérification spécifique à Windows.")
        if not _obsidian_cli().is_file():
            self.skipTest("Obsidian.com absent — voir TestObsidianInstalled.")

        try:
            result = subprocess.run(
                [str(_obsidian_cli()), "--version"],
                capture_output=True, text=True, timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            self.skipTest(f"Impossible d'invoquer la CLI Obsidian : {e}")

        if "unable to find Obsidian" in (result.stdout + result.stderr):
            self.skipTest(
                "Obsidian n'est pas actuellement lancé — la CLI ne peut pas répondre. "
                "Ouvrir Obsidian puis relancer ce test pour vérifier qu'il est up et fonctionne."
            )
        self.assertEqual(
            result.returncode, 0,
            f"CLI Obsidian a répondu avec un échec inattendu : {result.stdout}{result.stderr}",
        )


class TestVaultStructure(unittest.TestCase):
    def test_wiki_root_exists(self):
        self.assertTrue(WIKI_DIR.is_dir())

    def test_all_mode_b_subfolders_exist(self):
        for sub in WIKI_SUBFOLDERS:
            with self.subTest(subfolder=sub):
                self.assertTrue((WIKI_DIR / sub).is_dir(), f"wiki/{sub}/ manquant")

    def test_meta_files_exist(self):
        for name in ("index.md", "log.md", "hot.md", "overview.md"):
            with self.subTest(file=name):
                self.assertTrue((META_DIR / name).is_file(), f"_meta/{name} manquant")

    def test_templates_exist_for_each_mode_b_type(self):
        for sub in WIKI_SUBFOLDERS:
            # "dependencies" -> template "dependency.md" (singulier), les autres
            # suivent le singulier du nom de dossier.
            singular = {"dependencies": "dependency"}.get(sub, sub.rstrip("s"))
            with self.subTest(template=singular):
                self.assertTrue(
                    (TEMPLATES_DIR / f"{singular}.md").is_file(),
                    f"_templates/{singular}.md manquant",
                )

    def test_css_snippet_exists(self):
        self.assertTrue((OBSIDIAN_DIR / "snippets" / "vault-colors.css").is_file())

    def test_gitignore_covers_obsidian_workspace_files(self):
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        for entry in (".obsidian/workspace.json", ".trash/"):
            with self.subTest(entry=entry):
                self.assertIn(entry, gitignore)

    def test_at_least_one_page_per_mode_b_subfolder(self):
        for sub in WIKI_SUBFOLDERS:
            with self.subTest(subfolder=sub):
                pages = list((WIKI_DIR / sub).glob("*.md"))
                self.assertGreater(len(pages), 0, f"wiki/{sub}/ ne contient aucune page")


class TestPageFrontmatter(unittest.TestCase):
    def test_every_page_has_parseable_frontmatter(self):
        pages = [p for p in _all_vault_pages() if p not in PAGES_WITHOUT_FRONTMATTER]
        self.assertGreater(len(pages), 0, "Aucune page trouvée sous wiki/ ou _meta/")
        for page in pages:
            with self.subTest(page=str(page.relative_to(PROJECT_ROOT))):
                has_fm, block = _parse_frontmatter(page.read_text(encoding="utf-8"))
                self.assertTrue(has_fm, f"{page} : pas de frontmatter YAML valide (--- ... ---)")
                self.assertIn("type:", block, f"{page} : frontmatter sans champ 'type'")

    def test_module_pages_declare_type_module(self):
        for page in (WIKI_DIR / "modules").glob("*.md"):
            with self.subTest(page=page.name):
                _, block = _parse_frontmatter(page.read_text(encoding="utf-8"))
                self.assertIn("type: module", block)


class TestWikilinksResolve(unittest.TestCase):
    def test_all_wikilinks_point_to_existing_pages(self):
        page_names = {p.stem for p in _all_vault_pages()}
        broken: list[str] = []
        for page in _all_vault_pages():
            text = page.read_text(encoding="utf-8")
            for target in _extract_wikilinks(text):
                if target not in page_names:
                    broken.append(f"{page.relative_to(PROJECT_ROOT)} -> [[{target}]]")
        self.assertEqual(broken, [], "Wikilinks cassés trouvés :\n" + "\n".join(broken))

    def test_index_page_links_are_all_valid(self):
        # L'index est le point d'entrée principal — s'il a un lien cassé, la navigation
        # depuis _meta/index.md est immédiatement compromise.
        page_names = {p.stem for p in _all_vault_pages()}
        index_text = (META_DIR / "index.md").read_text(encoding="utf-8")
        targets = _extract_wikilinks(index_text)
        self.assertGreater(len(targets), 0)
        missing = targets - page_names
        self.assertEqual(missing, set())


class TestModuleCompiles(unittest.TestCase):
    """Auto-vérification : ce fichier de test lui-même doit rester syntaxiquement valide
    (équivalent programmatique de `python -m py_compile`, sans dépendre d'un appel Bash
    ad-hoc — cohérent avec run_tests.py comme seul point d'entrée de vérification)."""

    def test_this_test_file_compiles(self):
        try:
            py_compile.compile(str(Path(__file__)), doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"tests/test_obsidian_vault.py ne compile pas : {e}")


if __name__ == "__main__":
    unittest.main()
