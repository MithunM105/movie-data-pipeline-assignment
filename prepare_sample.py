"""Create a quota-sized MovieLens sample from the already-loaded SQLite database."""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


def read_movies(path: Path, limit: int) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) >= limit:
                break
        return rows, reader.fieldnames or []


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def copy_rows(source: sqlite3.Connection, target: sqlite3.Connection,
              table: str, where: str = "", params: tuple = ()) -> int:
    rows = source.execute(f"SELECT * FROM {table} {where}", params).fetchall()
    if not rows:
        return 0
    count = len(rows[0])
    target.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in range(count))})", rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--database", default="movie_data.db")
    parser.add_argument("--schema", default=str(Path(__file__).with_name("schema.sql")))
    parser.add_argument("--output-data", default="data_omdb_sample")
    parser.add_argument("--output-database", default="movie_data_omdb_sample.db")
    parser.add_argument("--movie-limit", type=int, default=1000)
    args = parser.parse_args()
    if args.movie_limit < 1:
        parser.error("--movie-limit must be positive")

    project = Path(__file__).parent
    movies_path = project / args.data_dir / "movies.csv"
    ratings_path = project / args.data_dir / "ratings.csv"
    source_db = project / args.database
    sample_dir = project / args.output_data
    sample_db = project / args.output_database
    if not source_db.is_file():
        raise FileNotFoundError(f"Run etl.py first to create {source_db}")

    sampled_movies, movie_columns = read_movies(movies_path, args.movie_limit)
    wanted_ids = {int(row["movieId"]) for row in sampled_movies}
    with sqlite3.connect(source_db) as source:
        cached_ids = {row[0] for row in source.execute(
            "SELECT movie_id FROM omdb_cache WHERE movie_id IN ({})".format(
                ",".join("?" for _ in wanted_ids)), tuple(wanted_ids))
        }
        movie_rows = [row for row in sampled_movies if int(row["movieId"]) in cached_ids]
        movie_ids = {int(row["movieId"]) for row in movie_rows}
        if not movie_ids:
            raise ValueError("No OMDb-cached movies found in the requested MovieLens sample")

        with ratings_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rating_columns = reader.fieldnames or []
            rating_rows = [row for row in reader if int(row["movieId"]) in movie_ids]

        sample_dir.mkdir(parents=True, exist_ok=True)
        write_csv(sample_dir / "movies.csv", movie_columns, movie_rows)
        write_csv(sample_dir / "ratings.csv", rating_columns, rating_rows)

        if sample_db.exists():
            raise FileExistsError(f"Sample database already exists: {sample_db}; choose a new --output-database")
        target = sqlite3.connect(sample_db)
        target.execute("PRAGMA foreign_keys = ON")
        try:
            target.executescript((project / args.schema).read_text(encoding="utf-8-sig"))
            ids = tuple(sorted(movie_ids))
            placeholders = ",".join("?" for _ in ids)
            with target:
                n_movies = copy_rows(source, target, "movies", f"WHERE movie_id IN ({placeholders})", ids)
                n_genres = copy_rows(source, target, "genres", "WHERE genre_id IN (SELECT DISTINCT genre_id FROM movie_genres WHERE movie_id IN (" + placeholders + "))", ids)
                n_links = copy_rows(source, target, "movie_genres", f"WHERE movie_id IN ({placeholders})", ids)
                n_ratings = copy_rows(source, target, "ratings", f"WHERE movie_id IN ({placeholders})", ids)
                n_cache = copy_rows(source, target, "omdb_cache", f"WHERE movie_id IN ({placeholders})", ids)
        finally:
            target.close()

    print(f"Created {sample_db}: {n_movies} movies, {n_ratings} ratings, "
          f"{n_genres} genres, {n_links} movie-genre links, {n_cache} cached OMDb lookups")


if __name__ == "__main__":
    main()
