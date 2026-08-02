"""Valida o contrato estático de dependências do pipeline."""

from __future__ import annotations

import ast
import re
import sys
import tomllib
import unittest
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_ROOT.parent
PYPROJECT_PATH = PIPELINE_ROOT / "pyproject.toml"
AUDIT_ROOTS = {
    "runtime": (PIPELINE_ROOT / "src", PIPELINE_ROOT / "scripts"),
    "research": (PIPELINE_ROOT / "research",),
    "test": (PIPELINE_ROOT / "tests",),
}
IMPORT_TO_DISTRIBUTION = {
    "dotenv": "python-dotenv",
    "psycopg2": "psycopg2-binary",
}

# Integração local deliberada, não uma distribuição do índice Python.
# O módulo é fornecido pelo projeto apontado por SESI_DB_DIR em execuções específicas.
LOCAL_INTEGRATION_IMPORTS = {
    "utils_educacao": "módulo local fornecido pelo diretório configurado em SESI_DB_DIR",
}


def _canonical_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_distribution_names(entries: list[str]) -> set[str]:
    names = set()
    for entry in entries:
        requirement = entry.partition(";")[0].strip()
        raw_name = re.split(r"[\s<>=!~\[]", requirement, maxsplit=1)[0]
        names.add(_canonical_distribution_name(raw_name))
    return names


def _local_import_names() -> set[str]:
    names = {"data_pipeline", "research", "scripts", "src"}
    for roots in AUDIT_ROOTS.values():
        for root in roots:
            for path in root.rglob("*.py"):
                names.add(path.stem)
    return names


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append(node.module.split(".", 1)[0])
    return imports


class DependencyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with PYPROJECT_PATH.open("rb") as stream:
            project = tomllib.load(stream)
        cls.runtime_dependencies = _declared_distribution_names(
            project["project"]["dependencies"]
        )
        cls.test_dependencies = _declared_distribution_names(
            project["dependency-groups"]["test"]
        )

    def test_dependency_groups_are_separated(self) -> None:
        self.assertNotIn("pytest", self.runtime_dependencies)
        self.assertIn("pytest", self.test_dependencies)
        self.assertTrue(
            self.runtime_dependencies.isdisjoint(self.test_dependencies),
            "Dependências de teste não devem ser repetidas no runtime.",
        )

    def test_required_direct_dependencies_are_declared(self) -> None:
        required_runtime = {
            "numpy",
            "openpyxl",
            "pandas",
            "psycopg2-binary",
            "pypdf",
            "python-dotenv",
            "requests",
            "sqlalchemy",
            "supabase",
        }
        self.assertEqual(
            required_runtime - self.runtime_dependencies,
            set(),
            "Dependências diretas ou drivers obrigatórios ausentes do runtime.",
        )

    def test_legacy_requirements_is_absent(self) -> None:
        self.assertFalse(
            (PIPELINE_ROOT / "requirements.txt").exists(),
            "data_pipeline/requirements.txt foi aposentado; use pyproject.toml e uv.lock.",
        )

    def test_direct_imports_are_declared(self) -> None:
        local_imports = _local_import_names()
        violations = []
        for classification, roots in AUDIT_ROOTS.items():
            allowed = set(self.runtime_dependencies)
            if classification == "test":
                allowed.update(self.test_dependencies)
            for root in roots:
                for path in sorted(root.rglob("*.py")):
                    for imported_name in sorted(set(_absolute_imports(path))):
                        if (
                            imported_name in sys.stdlib_module_names
                            or imported_name in local_imports
                            or imported_name in LOCAL_INTEGRATION_IMPORTS
                        ):
                            continue
                        distribution = _canonical_distribution_name(
                            IMPORT_TO_DISTRIBUTION.get(imported_name, imported_name)
                        )
                        if distribution not in allowed:
                            relative_path = path.relative_to(REPO_ROOT).as_posix()
                            violations.append(
                                f"{relative_path}: import {imported_name!r} exige "
                                f"a dependência {distribution!r} em {classification}."
                            )
        self.assertEqual(
            violations,
            [],
            "Imports externos sem declaração apropriada:\n" + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
