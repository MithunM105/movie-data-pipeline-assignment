# MovieLens Data Pipeline

## Overview

This project loads MovieLens movie and rating CSV files, adds available movie details from OMDb, and saves the results in SQLite. The SQL queries in `queries.sql` analyze the loaded data.

## Files

- `etl.py` — reads, cleans, enriches, and loads the data.
- `schema.sql` — creates the database tables.
- `queries.sql` — contains the assignment queries.
- `data/` — MovieLens CSV input files.
- `data_omdb_sample/` and `movie_data_omdb_sample.db` — 1,000-movie sample for a quick demo.

## Setup and run

Python 3.10+ is required. From the project folder in PowerShell, run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

Load all MovieLens CSV data without OMDb enrichment:

```powershell
py etl.py --data-dir data --database movie_data.db --skip-omdb
```

To also fetch OMDb details, set your API key and run the ETL:

```powershell
$env:OMDB_API_KEY = "your_omdb_key"
py etl.py --data-dir data --database movie_data.db
```

The script creates the tables automatically. The API key should be kept private and out of the project files. The sample database is already included; open it with DB Browser for SQLite and run `queries.sql` in **Execute SQL**. A SQLite database is a binary file, so use DB Browser rather than opening it as text in VS Code.

## Design and assumptions

SQLite keeps the project simple to run. Movies, genres, and ratings are stored in related tables; a movie can have multiple genres. MovieLens IDs identify movies, and ratings use user, movie, and timestamp as their key. OMDb fields can be empty when a title is not found. The pipeline caches completed OMDb lookups and can be rerun without adding duplicate records. Release decade is derived from the movie year.

## Challenges

The free OMDb key allows **1,000 requests per day**, while MovieLens small contains **9,742 movies**. I included a 1,000-movie sample for the demo; the cache lets OMDb enrichment continue on later days. Movie titles may not match OMDb exactly, so the script uses the year when available and continues loading when details are missing.

