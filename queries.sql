-- 1. Movie with highest average rating. Tie-break by number of ratings, then title.
SELECT m.movie_id, m.title, ROUND(AVG(r.rating), 3) AS average_rating,
       COUNT(*) AS rating_count
FROM movies AS m
JOIN ratings AS r ON r.movie_id = m.movie_id
GROUP BY m.movie_id, m.title
ORDER BY average_rating DESC, rating_count DESC, m.title
LIMIT 1;

-- 2. Top five genres by average rating across all ratings for movies in each genre.
SELECT g.name AS genre, ROUND(AVG(r.rating), 3) AS average_rating,
       COUNT(*) AS rating_count
FROM genres AS g
JOIN movie_genres AS mg ON mg.genre_id = g.genre_id
JOIN ratings AS r ON r.movie_id = mg.movie_id
GROUP BY g.genre_id, g.name
ORDER BY average_rating DESC, rating_count DESC, g.name
LIMIT 5;

-- 3. Director credited with the most movies (excludes unknown directors).
SELECT director, COUNT(*) AS movie_count
FROM movies
WHERE director IS NOT NULL AND TRIM(director) <> ''
GROUP BY director
ORDER BY movie_count DESC, director
LIMIT 1;

-- 4. Average user rating by release year.
SELECT m.release_year, ROUND(AVG(r.rating), 3) AS average_rating,
       COUNT(*) AS rating_count
FROM movies AS m
JOIN ratings AS r ON r.movie_id = m.movie_id
WHERE m.release_year IS NOT NULL
GROUP BY m.release_year
ORDER BY m.release_year;
