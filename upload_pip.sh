# 1) Tools installieren
# python -m pip install --upgrade build twine

# 2) Paket bauen (sdist + wheel in ./dist/)
python -m build

# 3) Artefakte prüfen
twine check dist/*

# 4a) Upload zu TestPyPI
twine upload --repository testpypi dist/*

# 4b) Upload zu PyPI
twine upload dist/*