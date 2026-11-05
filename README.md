# MovieLens + OMDb Data Pipeline

A compact Python ETL project that imports MovieLens small movie and rating CSVs, enriches movies through OMDb, and loads query-ready tables into SQLite.

## Requirements

- Python 3.10+
- MovieLens **small** dataset from [GroupLens](https://grouplens.org/datasets/movielens/latest/)
- An OMDb API key (free keys can be requested at [omdbapi.com](https://www.omdbapi.com/apikey.aspx))

SQLite is included with Python. Only `requests` is an external package.

## Run it

1. Download and extract the MovieLens small archive. Put `movies.csv` and `ratings.csv` in a `data/` directory beside `etl.py`.
2. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Set the API key as an environment variable (keeps the key out of source control):

   ```bash
   # Windows PowerShell
   $env:OMDB_API_KEY = "your_key"
   # macOS/Linux
   export OMDB_API_KEY="your_key"
   ```

4. Run the pipeline:

   ```bash
   python etl.py --data-dir data --database movie_data.db
   ```

   The schema is applied automatically. You can override request pacing with `--delay 0.3` or provide paths using `--database` and `--schema`. The output database is local and should not be committed if it contains data or secrets. The supplied MovieLens CSVs are included in `data/`. To load them without an OMDb key, run `python etl.py --data-dir data --database movie_data.db --skip-omdb`; OMDb-derived columns remain null. When a key is available, omit `--skip-omdb` to perform enrichment.

5. Run the four analytical statements in `queries.sql` against `movie_data.db` using `sqlite3`, DB Browser for SQLite, or Python's `sqlite3` module.

### Run from Visual Studio Code on Windows

Open this project folder in VS Code, then press `Ctrl+Shift+P`, choose **Tasks: Run Task**, and select **Run MovieLens sample ETL**. The task uses the bundled quota-sized sample and `--skip-omdb`, so it does not consume API requests. The integrated terminal displays the result. To install or update the Python dependency first, run **Install Python requirements** from the same task menu.

To run the complete local MovieLens CSV load from the VS Code terminal, use:

```powershell
py etl.py --data-dir data --database movie_data.db --skip-omdb
```

To perform OMDb enrichment, omit `--skip-omdb` and set `OMDB_API_KEY` in the terminal environment. The API's free daily limit means enrichment can take multiple runs; cached lookups resume on later runs.

## Quota-sized assignment sample

The free OMDb key permits 1,000 daily requests, while MovieLens small contains 9,742 movies. The full local MovieLens data is retained in `movie_data.db`; repeated ETL runs cache successful and not-found API results so enrichment can continue on later days. To build a one-day, quota-sized analysis sample from the first 1,000 movies already looked up, run:

```bash
python prepare_sample.py --movie-limit 1000
```

This creates `data_omdb_sample/` with those movies and their ratings, plus `movie_data_omdb_sample.db` with the corresponding cached OMDb results. Run the queries against that sample database for a bounded assignment demo. Ratings and genre questions are complete for the sample; the director query counts available OMDb director credits and excludes titles that OMDb did not find. Its result should therefore be presented as sample-scoped and as based on available director metadata.

## Design choices and assumptions

- SQLite keeps setup friction low while providing relational integrity. `schema.sql` is also a standalone schema deployment script.
- MovieLens `movieId` remains the movie key. Genres are stored in `genres` and `movie_genres`; ratings refer to a movie and use `(user_id, movie_id, rated_at)` as their natural key. This retains records even if the same user rates a movie again at a different time.
- The year in the MovieLens title is preferred as a lookup hint; OMDb's release year is used when returned. `decade` is derived from the selected year. The original title is kept as supplied by MovieLens.
- OMDb enrichment fields are nullable. A not-found title or exhausted transient retries does not stop ingestion. The local CSV-only mode can be used before an API key is configured. Successful raw OMDb responses are retained as JSON for traceability.
- API requests use a timeout, three attempts with exponential backoff for transport/HTTP/JSON errors, and a configurable delay between uncached lookups. The key is read from `OMDB_API_KEY`.
- OMDb successes and definitive not-found results are stored in `omdb_cache`. If OMDb reports a quota, key, or service error, lookup requests pause for the rest of that run while local ingestion finishes. Run the same command again later to resume at the next uncached movie; completed lookups are not repeated.
- The load is idempotent: movie rows are upserted, genre links are replaced for each imported movie, and ratings are upserted by their natural key. OMDb responses are cached so reruns can resume enrichment without duplicating API calls.
- Box Office is parsed to an integer USD amount when OMDb supplies a parseable value. Currency conversion is not attempted.

## Challenges and handling

Movie titles can be ambiguous or absent from OMDb. The pipeline supplies a parsed year to narrow title search, treats explicit API misses as nullable enrichment, and reports exhausted request failures. Invalid CSV rating rows are skipped with a diagnostic; database constraints protect referential integrity and valid rating ranges. The free OMDb key allows 1,000 daily requests, so full enrichment of this dataset takes multiple days. The persistent cache and quota pause make that process resumable.

## Production extensions

For larger or scheduled loads, add structured logs and metrics, a staging table with validation reports, and incremental change detection. A server database and orchestrator would support concurrent analytics and retries at task level. IMDb IDs could be reconciled from a dedicated crosswalk instead of title matching.

## Repository contents

- `etl.py`: extraction, transformation, and idempotent SQLite loading
- `prepare_sample.py`: create a quota-sized CSV and database sample from the cached full load
- `schema.sql`: relational schema and indexes
- `queries.sql`: requested analytical queries
- `requirements.txt`: Python dependency
