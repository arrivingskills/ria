# ria

## places.py — find similar points of interest

Find POIs around the globe that are similar to a named place, using category
similarity (TF-IDF + cosine similarity) over `~/data/bronze/poi.csv`.

```bash
python -m ria.places "Eiffel Tower"          # top 10 similar POIs
python -m ria.places "Pemba Island" -n 5 -v  # top 5, show shared categories
python -m ria.places --csv /path/poi.csv "Mount Fiske Glacier"
python -m ria.places                          # interactive mode
```

Run from the repo root with the virtualenv Python, e.g.:

```bash
.venv/bin/python src/ria/places.py "Pemba Island"
```
