# MovieLens Data Pipeline

## Overview

I built a Python ETL pipeline that combines MovieLens movie and rating data with extra movie details from OMDb, stores the result in SQLite, and answers analysis questions with SQL.

## Pipeline

1. **Extract:** Read `movies.csv` and `ratings.csv` from `data/` and request movie details from OMDb.
2. **Transform:** Clean the input, split movie genres into related records, and derive each movie's decade.
3. **Load:** Save movies, genres, ratings, and available OMDb details to SQLite. The script can be rerun without duplicating records.
4. **Analyze:** Run the four queries in `queries.sql` against the database.

## Run the project

Requirements: Python 3.10+ and an OMDb API key for enrichment. Install the dependency from the project folder:

```powershell
py -m pip install -r requirements.txt
```

Load MovieLens data without OMDb enrichment:

```powershell
py etl.py --data-dir data --database movie_data.db --skip-omdb
```

Load MovieLens data and request OMDb details:

```powershell
$env:OMDB_API_KEY = "your_omdb_key"
py etl.py --data-dir data --database movie_data.db
```

The repository includes a 1,000-movie sample database. Open `movie_data_omdb_sample.db` in DB Browser for SQLite and run `queries.sql` from **Execute SQL**.

## Design choices

I used SQLite to keep the project easy to run. Movies, genres, and ratings are stored in related tables, with a separate link table for movie genres. MovieLens IDs identify movies; ratings use the user, movie, and timestamp together. Missing OMDb details are left empty. The database caches completed lookups and uses keys to prevent duplicate records.

## Challenges

OMDb allows 1,000 free requests per day, but MovieLens small has 9,742 movies. I included a 1,000-movie sample and cached lookups so enrichment can resume later. Unmatched titles keep missing OMDb details; the MovieLens data still loads.


