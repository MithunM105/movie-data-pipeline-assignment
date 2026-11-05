# MovieLens Movie Data Pipeline

## Overview

This project builds a small, repeatable ETL pipeline for the MovieLens small dataset. It reads movie and rating CSV files, adds available movie details from OMDb, transforms the records, and stores the result in a relational SQLite database. The database can then be queried with the four analysis statements in `queries.sql`.

The repository includes the MovieLens CSV inputs and a 1,000-movie sample database for quick review. The full MovieLens dataset contains 9,742 movies; OMDb's free daily request limit means the full dataset's enrichment may require multiple runs across multiple days.

## Project files

```text
movie-data-pipeline-assignment/
├── etl.py
├── schema.sql
├── queries.sql
├── README.md
├── requirements.txt
├── prepare_sample.py
├── data/                       # MovieLens small CSV inputs
├── data_omdb_sample/           # Quota-sized sample CSV inputs
└── movie_data_omdb_sample.db   # Sample database for the assignment queries
```

`movie_data.db` is generated locally by the ETL command and is not committed. The sample database is included so the queries can be reviewed without first making OMDb requests.

## Requirements

- Python 3.10 or later
- MovieLens small dataset (`movies.csv` and `ratings.csv`), available from [GroupLens](https://grouplens.org/datasets/movielens/latest/). The repository already includes these files in `data/`.
- An OMDb API key for enrichment. Request a key at [omdbapi.com](https://www.omdbapi.com/apikey.aspx).

SQLite is included with Python. The only third-party Python package is `requests`.

## Setup and run

From the project root, create a virtual environment and install the dependency:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

On macOS or Linux, use `python3` in place of `py`, and activate with `source .venv/bin/activate`.

To load the MovieLens files without calling OMDb:

```powershell
py etl.py --data-dir data --database movie_data.db --skip-omdb
```

To also enrich movies from OMDb, set the API key in the current PowerShell session, then run the pipeline:

```powershell
$env:OMDB_API_KEY = "your_omdb_key"
py etl.py --data-dir data --database movie_data.db
```

On macOS or Linux, set the key with `export OMDB_API_KEY="your_omdb_key"` and run `python3 etl.py --data-dir data --database movie_data.db`. Keep the key in your environment; do not put it in a source file or commit it to Git.

The script applies `schema.sql` automatically and creates the database file if needed. It uses a short delay between uncached API lookups. OMDb results are cached in the database, so a later run can continue with movies that have not been looked up yet. OMDb not-found results do not prevent MovieLens records from loading. If the service reports a quota or key error, the script pauses additional lookups for that run and completes the local data load.

### Run the included sample

The sample is already built. To recreate its CSV inputs and database from the full database's cached OMDb results, run:

```powershell
py prepare_sample.py --movie-limit 1000
```

To rebuild the sample database from its CSV files without making API calls:

```powershell
py etl.py --data-dir data_omdb_sample --database movie_data_omdb_sample.db --skip-omdb
```

### Run the analysis queries

Open `movie_data_omdb_sample.db` in DB Browser for SQLite, choose **Execute SQL**, open or paste the statements from `queries.sql`, and run them. The queries also work with `movie_data.db` after the full CSV load. Query 3 counts only directors returned by OMDb, so its result reflects the available director metadata in the selected database.

## Data model and design choices

- `movies` stores one row per MovieLens movie ID and its available OMDb details.
- `genres` stores unique genre names. `movie_genres` links movies to genres in a many-to-many relationship.
- `ratings` stores each user's rating and UTC timestamp. Its composite key is `(user_id, movie_id, rated_at)`.
- `omdb_cache` stores successful lookups and definitive not-found results to avoid repeating API requests on later runs.
- SQLite was chosen because it is lightweight, relational, and requires no separate database server for this assignment.
- The MovieLens movie ID is the stable key. OMDb lookups use the title and, when available, the year parsed from the MovieLens title. Titles are not guaranteed to match OMDb exactly, so enrichment fields can be missing.
- Missing OMDb values are stored as `NULL`. MovieLens genres remain normalized into separate genre and link tables. A decade column is derived from the selected release year.
- Box Office values are stored as integer USD amounts when OMDb provides a parseable value. No currency conversion is performed.

## Idempotency and data quality

Running the ETL more than once does not duplicate movie, genre-link, or rating records. Movies are upserted by MovieLens ID, genre links are rebuilt from the current CSV row, and ratings are upserted by their composite key. The schema enforces foreign keys and rating bounds. Invalid rating rows are skipped with a diagnostic, while missing movie metadata does not block the load.

## Challenges I faced and how I handled them

- **OMDb's daily request limit:** The free OMDb key allows 1,000 requests per day. MovieLens small has 9,742 movies, so I could not fetch OMDb details for every movie in one day. I included a 1,000-movie sample for a ready-to-run demonstration. The ETL cache saves completed lookups, so I can run the full dataset again on later days and continue enriching movies that were not looked up yet. The MovieLens CSV data can still be loaded even when OMDb lookups pause.
- **Movie titles do not always match:** Some MovieLens titles may not be found in OMDb or may have different title text. I include the year in the lookup when it is available, keep missing OMDb fields empty, and continue loading the rest of the movies instead of stopping the whole pipeline.
- **Keeping the data connected:** Movies, genres, and ratings are related, so I used separate tables and keys to prevent duplicate records and keep those links consistent. I also made the load safe to rerun, which helped me check the results without creating duplicate movies or ratings.
- **Opening the database:** A SQLite database is a binary file, so it does not display as readable text in VS Code. I use VS Code for the Python and SQL files, and DB Browser for SQLite to open the database and run the queries.

## Simple project explanation

“I used Python to read the MovieLens movie and rating files, add extra movie information from OMDb when it is available, and save the results in SQLite. I separated movies, genres, and ratings into related tables, then wrote SQL queries to analyze the data. One challenge was that the free OMDb key allows only 1,000 requests per day, while the dataset has 9,742 movies. I prepared a 1,000-movie sample for the demo and added a cache so the remaining OMDb lookups can continue on later days.”

## Assignment SQL

`queries.sql` contains four example analyses:

1. Movie with the highest average rating.
2. Five genres with the highest average rating.
3. Director credited with the most movies in the available OMDb data.
4. Average rating by release year.



