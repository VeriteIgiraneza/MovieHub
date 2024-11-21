from flask import Flask, jsonify, render_template, request, redirect, g, url_for, session
import mysql.connector
# from flask_bcrypt import Bcrypt
# import re
import logging
# from datetime import timedelta

# from functools import wraps


app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    try:
        return mysql.connector.connect(
            host="cse335-fall-2024.c924km8o85q2.us-east-1.rds.amazonaws.com",
            user="v0igir01",
            password="2c3e13850d",
            database="student_v0igir01_db",
            connection_timeout=5
        )
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return None


def get_db():
    if 'db' not in g:
        g.db = get_db_connection()
        if not g.db:
            raise RuntimeError("Could not connect to MySQL")
        g.cursor = g.db.cursor(buffered=True)
    return g.db, g.cursor


def execute_query(cursor, query, params=None):
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    except mysql.connector.Error as err:
        logger.error(f"Query execution error: {err}")
        logger.error(f"Query: {query}")
        logger.error(f"Parameters: {params}")
        return []


def get_genres():
    try:
        db, cursor = get_db()
        return execute_query(cursor, "SELECT GenreID, GenreName FROM Genres ORDER BY GenreName")
    except Exception as err:
        logger.error(f"Failed to fetch genres: {err}")
        return []


def validate_rating(rating):
    try:
        rating = float(rating)
        return 0 <= rating <= 10
    except (ValueError, TypeError):
        return False


def build_movie_query(search_params):
    """Helper function to build the movie query based on search parameters."""
    base_query = """
        SELECT DISTINCT
            m.ID,
            m.Title,
            ROUND(r.Rating, 1) as Rating,
            m.Runtime,
            GROUP_CONCAT(DISTINCT g.GenreName ORDER BY g.GenreName SEPARATOR ', ') as Genres,
            m.Metascore,
            m.Plot,
            GROUP_CONCAT(DISTINCT d.DirectorName ORDER BY d.DirectorName SEPARATOR ', ') as Directors,
            GROUP_CONCAT(DISTINCT s.StarName ORDER BY s.StarName SEPARATOR ', ') as Stars,
            r.Votes,
            CONCAT('$', FORMAT(m.Gross, 2)) as Gross,
            m.Link
        FROM Movies m
        LEFT JOIN Ratings r ON m.ID = r.MovieID
        LEFT JOIN MovieGenres mg ON m.ID = mg.MovieID
        LEFT JOIN Genres g ON mg.GenreID = g.GenreID
        LEFT JOIN MovieDirectors md ON m.ID = md.MovieID
        LEFT JOIN Directors d ON md.DirectorID = d.DirectorID
        LEFT JOIN MovieStars ms ON m.ID = ms.MovieID
        LEFT JOIN Stars s ON ms.StarID = s.StarID
    """

    where_clauses = []
    params = []

    if search_params.get('query'):
        query = search_params['query']
        search_type = search_params.get('search_type', 'all')

        if search_type == 'movie':
            where_clauses.append("m.Title LIKE %s")
            params.append(f'%{query}%')
        elif search_type == 'director':
            where_clauses.append("d.DirectorName LIKE %s")
            params.append(f'%{query}%')
        elif search_type == 'star':
            where_clauses.append("s.StarName LIKE %s")
            params.append(f'%{query}%')
        else:
            where_clauses.append("(m.Title LIKE %s OR d.DirectorName LIKE %s OR s.StarName LIKE %s)")
            params.extend([f'%{query}%'] * 3)

    if search_params.get('min_rating'):
        where_clauses.append("r.Rating >= %s")
        params.append(float(search_params['min_rating']))

    if search_params.get('max_rating'):
        where_clauses.append("r.Rating <= %s")
        params.append(float(search_params['max_rating']))

    if search_params.get('genre'):
        where_clauses.append("g.GenreID = %s")
        params.append(int(search_params['genre']))

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    group_by = """
        GROUP BY 
            m.ID, 
            m.Title, 
            r.Rating, 
            m.Runtime,
            m.Metascore,
            m.Plot,
            r.Votes,
            m.Gross,
            m.Link
    """

    sort_mapping = {
        'rating_desc': 'COALESCE(r.Rating, 0) DESC',
        'rating_asc': 'COALESCE(r.Rating, 0) ASC',
        'votes_desc': 'COALESCE(r.Votes, 0) DESC',
        'name_asc': 'm.Title ASC'
    }
    order_by = sort_mapping.get(search_params.get('sort'), 'COALESCE(r.Rating, 0) DESC')

    final_query = f"{base_query} WHERE {where_clause} {group_by} ORDER BY {order_by} LIMIT 100"

    return final_query, params


def get_genre_name(genre_id):
    try:
        db, cursor = get_db()
        cursor.execute("SELECT GenreName FROM Genres WHERE GenreID = %s", (genre_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as err:
        logger.error(f"Failed to fetch genre name: {err}")
        return None



@app.route('/')
def index():
    try:
        db, cursor = get_db()
        # Get genres for dropdown
        genres_query = "SELECT GenreID, GenreName FROM Genres ORDER BY GenreName"
        cursor.execute(genres_query)
        genres = cursor.fetchall()

        # Get movies with all related data
        movies_query = """
            SELECT DISTINCT
                m.ID,
                m.Title,
                ROUND(r.Rating, 1) as Rating,
                m.Runtime,
                GROUP_CONCAT(DISTINCT g.GenreName ORDER BY g.GenreName SEPARATOR ', ') as Genres,
                m.Metascore,
                m.Plot,
                GROUP_CONCAT(DISTINCT d.DirectorName ORDER BY d.DirectorName SEPARATOR ', ') as Directors,
                GROUP_CONCAT(DISTINCT s.StarName ORDER BY s.StarName SEPARATOR ', ') as Stars,
                r.Votes,
                CONCAT('$', FORMAT(m.Gross, 2)) as Gross,
                m.Link
            FROM Movies m
            LEFT JOIN Ratings r ON m.ID = r.MovieID
            LEFT JOIN MovieGenres mg ON m.ID = mg.MovieID
            LEFT JOIN Genres g ON mg.GenreID = g.GenreID
            LEFT JOIN MovieDirectors md ON m.ID = md.MovieID
            LEFT JOIN Directors d ON md.DirectorID = d.DirectorID
            LEFT JOIN MovieStars ms ON m.ID = ms.MovieID
            LEFT JOIN Stars s ON ms.StarID = s.StarID
            GROUP BY m.ID, m.Title, r.Rating, m.Runtime, m.Metascore, m.Plot, r.Votes, m.Gross, m.Link
            ORDER BY r.Rating DESC
            LIMIT 9999
        """
        cursor.execute(movies_query)
        movies = cursor.fetchall()

        return render_template('index.html',
                             movies=movies,
                             genres=genres)

    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('index.html',
                               error="An error occurred while searching movies",
                               error_context='search',
                               genres=get_genres())


@app.route('/filter')
def filter_movies():
    try:
        min_rating = request.args.get('min_rating')
        max_rating = request.args.get('max_rating')
        genre = request.args.get('genre')
        sort = request.args.get('sort', 'rating_desc')

        search_params = {'sort': sort}
        rating_range = None
        genre_name = None

        if min_rating or max_rating:
            if min_rating and not validate_rating(min_rating):
                return render_template('index.html',
                                       error="Invalid minimum rating",
                                       error_context='search',
                                       genres=get_genres())
            if max_rating and not validate_rating(max_rating):
                return render_template('index.html',
                                       error="Invalid maximum rating",
                                       error_context='search',
                                       genres=get_genres())

            search_params['min_rating'] = min_rating
            search_params['max_rating'] = max_rating

            if min_rating and max_rating:
                rating_range = f"{min_rating} - {max_rating}"
            elif min_rating:
                rating_range = f"{min_rating}+"
            else:
                rating_range = f"Up to {max_rating}"

        if genre:
            search_params['genre'] = genre
            genre_name = get_genre_name(genre)

        db, cursor = get_db()
        query, params = build_movie_query(search_params)
        movies = execute_query(cursor, query, params)
        genres = get_genres()

        return render_template('index.html',
                               movies=movies,
                               genres=genres,
                               filter_applied=True,
                               rating_range=rating_range,
                               selected_genre=genre,
                               genre_name=genre_name)
    except Exception as e:
        logger.error(f"Error in filter route: {e}")
        return render_template('index.html',
                               error="An error occurred while searching movies",
                               error_context='search',
                               genres=get_genres())

@app.route('/search')
def search():
    try:
        search_params = {
            'query': request.args.get('query', '').strip(),
            'search_type': request.args.get('search_type', 'all'),
            'min_rating': request.args.get('min_rating'),
            'max_rating': request.args.get('max_rating'),
            'genre': request.args.get('genre'),
            'sort': request.args.get('sort', 'rating_desc')
        }

        # Validate ratings
        if search_params['min_rating'] and not validate_rating(search_params['min_rating']):
            return render_template('index.html',
                                   error="Invalid minimum rating",
                                   error_context='search',
                                   genres=get_genres())
        if search_params['max_rating'] and not validate_rating(search_params['max_rating']):
            return render_template('index.html',
                                   error="Invalid maximum rating",
                                   error_context='search',
                                   gernes=get_genres())

        db, cursor = get_db()
        query, params = build_movie_query(search_params)
        movies = execute_query(cursor, query, params)
        genres = get_genres()

        return render_template('index.html',
                               movies=movies,
                               genres=genres,
                               search_params=search_params)
    except Exception as e:
        logger.error(f"Error in search route: {e}")
        return render_template('index.html',
                               error="An error occurred while searching movies",
                               error_context='search',
                               genres=get_genres())

@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop('db', None)
    cursor = g.pop('cursor', None)

    if cursor is not None:
        cursor.close()
    if db is not None:
        db.close()

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html',
                           error="Page not found",
                           error_context='search'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('index.html',
                           error="Internal server error",
                           error_context='search'), 500


@app.route('/dashboard')
def dashboard():
    try:
        db, cursor = get_db()
        # Get all movies for the dashboard
        query = """
            SELECT 
                m.ID,
                m.Title,
                m.Runtime,
                m.Metascore,
                m.Plot,
                m.Gross,
                GROUP_CONCAT(DISTINCT g.GenreName) as Genres,
                GROUP_CONCAT(DISTINCT d.DirectorName) as Directors,
                GROUP_CONCAT(DISTINCT s.StarName) as Stars,
                r.Rating,
                r.Votes
            FROM Movies m
            LEFT JOIN Ratings r ON m.ID = r.MovieID
            LEFT JOIN MovieGenres mg ON m.ID = mg.MovieID
            LEFT JOIN Genres g ON mg.GenreID = g.GenreID
            LEFT JOIN MovieDirectors md ON m.ID = md.MovieID
            LEFT JOIN Directors d ON md.DirectorID = d.DirectorID
            LEFT JOIN MovieStars ms ON m.ID = ms.MovieID
            LEFT JOIN Stars s ON ms.StarID = s.StarID
            GROUP BY m.ID
            ORDER BY m.Title
        """
        movies = execute_query(cursor, query)
        genres = get_genres()
        return render_template('dashboard.html',
                               movies=movies,
                               genres=genres)
                               # username=session.get('username'))
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return redirect(url_for('index'))


def check_duplicate_title(cursor, title):
    """Check if a movie with this title already exists"""
    cursor.execute("SELECT ID FROM Movies WHERE Title = %s", (title,))
    return cursor.fetchone() is not None


def insert_movie(cursor, movie_data):
    """Insert basic movie info and return the movie ID"""
    insert_movie_query = """
        INSERT INTO Movies (Title, Runtime, Metascore, Plot, Gross, Link)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(insert_movie_query, (
        movie_data['title'],
        movie_data['runtime'],
        movie_data['metascore'],
        movie_data['plot'],
        movie_data['gross'],
        movie_data['link']
    ))
    return cursor.lastrowid


def insert_directors(cursor, movie_id, directors_string):
    """Insert directors and link them to the movie"""
    if not directors_string:
        return

    directors = [d.strip() for d in directors_string.split(',')]
    for director in directors:
        # Insert director if not exists
        cursor.execute("INSERT IGNORE INTO Directors (DirectorName) VALUES (%s)", (director,))
        cursor.execute("SELECT DirectorID FROM Directors WHERE DirectorName = %s", (director,))
        director_id = cursor.fetchone()[0]

        # Link director to movie
        cursor.execute("INSERT INTO MovieDirectors (MovieID, DirectorID) VALUES (%s, %s)",
                       (movie_id, director_id))


def insert_stars(cursor, movie_id, stars_string):
    """Insert stars and link them to the movie"""
    if not stars_string:
        return

    stars = [s.strip() for s in stars_string.split(',')]
    for star in stars:
        # Insert star if not exists
        cursor.execute("INSERT IGNORE INTO Stars (StarName) VALUES (%s)", (star,))
        cursor.execute("SELECT StarID FROM Stars WHERE StarName = %s", (star,))
        star_id = cursor.fetchone()[0]

        # Link star to movie
        cursor.execute("INSERT INTO MovieStars (MovieID, StarID) VALUES (%s, %s)",
                       (movie_id, star_id))


def insert_genres(cursor, movie_id, genre_ids):
    """Link selected genres to the movie"""
    if not genre_ids:
        return

    for genre_id in genre_ids:
        cursor.execute("INSERT INTO MovieGenres (MovieID, GenreID) VALUES (%s, %s)",
                       (movie_id, genre_id))


def insert_rating(cursor, movie_id, rating, votes):
    """Insert movie rating"""
    if rating:
        cursor.execute("""
            INSERT INTO Ratings (MovieID, Rating, Votes)
            VALUES (%s, %s, %s)
        """, (movie_id, rating, votes or 0))


@app.route('/add_movie', methods=['POST'])
def add_movie():
    try:
        db, cursor = get_db()

        # Get form data
        movie_data = {
            'title': request.form.get('title'),
            'runtime': request.form.get('runtime'),
            'metascore': request.form.get('metascore'),
            'plot': request.form.get('plot'),
            'gross': request.form.get('gross'),
            'link': request.form.get('link'),
            'directors': request.form.get('directors'),
            'stars': request.form.get('stars')
        }

        rating = request.form.get('rating')
        votes = request.form.get('votes')
        genre_ids = request.form.getlist('genres')

        # Validate required fields
        if not movie_data['title']:
            return render_template('index.html',
                                   error="Title is required",
                                   error_context='add-movie',
                                   genres=get_genres(),
                                   form_data=movie_data,
                                   is_add_movie=True)

        # Check for duplicate title
        if check_duplicate_title(cursor, movie_data['title']):
            return render_template('index.html',
                                   error=f"A movie with the title '{movie_data['title']}' already exists in the database.",
                                   error_context='add-movie',
                                   genres=get_genres(),
                                   form_data=movie_data,
                                   is_add_movie=True)

        # Begin transaction
        cursor.execute("START TRANSACTION")

        try:
            # Insert movie and get its ID
            movie_id = insert_movie(cursor, movie_data)

            # Insert related data
            insert_directors(cursor, movie_id, movie_data['directors'])
            insert_stars(cursor, movie_id, movie_data['stars'])
            insert_genres(cursor, movie_id, genre_ids)
            insert_rating(cursor, movie_id, rating, votes)

            # Commit transaction
            db.commit()

            return redirect(url_for('index'))

        except Exception as e:
            # Rollback in case of error
            db.rollback()
            logger.error(f"Error adding movie: {e}")
            return render_template('index.html',
                                   error="Failed to add movie. Please try again.",
                                   error_context='add-movie',
                                   genres=get_genres(),
                                   form_data=movie_data)  # Pass back the form data to preserve user input

    except Exception as e:
        logger.error(f"Database error: {e}")
        return render_template('index.html',
                               error="Database error occurred. Please try again.",
                               genres=get_genres(),
                               form_data=movie_data)  # Pass back the form data to preserve user input


def get_movies():
    """Get all movies with their related data"""
    db, cursor = get_db()
    movies_query = """
        SELECT DISTINCT
            m.ID,
            m.Title,
            ROUND(r.Rating, 1) as Rating,
            m.Runtime,
            GROUP_CONCAT(DISTINCT g.GenreName ORDER BY g.GenreName SEPARATOR ', ') as Genres,
            m.Metascore,
            m.Plot,
            GROUP_CONCAT(DISTINCT d.DirectorName ORDER BY d.DirectorName SEPARATOR ', ') as Directors,
            GROUP_CONCAT(DISTINCT s.StarName ORDER BY s.StarName SEPARATOR ', ') as Stars,
            r.Votes,
            CONCAT('$', FORMAT(m.Gross, 2)) as Gross,
            m.Link
        FROM Movies m
        LEFT JOIN Ratings r ON m.ID = r.MovieID
        LEFT JOIN MovieGenres mg ON m.ID = mg.MovieID
        LEFT JOIN Genres g ON mg.GenreID = g.GenreID
        LEFT JOIN MovieDirectors md ON m.ID = md.MovieID
        LEFT JOIN Directors d ON md.DirectorID = d.DirectorID
        LEFT JOIN MovieStars ms ON m.ID = ms.MovieID
        LEFT JOIN Stars s ON ms.StarID = s.StarID
        GROUP BY m.ID, m.Title, r.Rating, m.Runtime, m.Metascore, m.Plot, r.Votes, m.Gross, m.Link
        ORDER BY r.Rating DESC
        LIMIT 9999
    """
    cursor.execute(movies_query)
    return cursor.fetchall()




if __name__ == '__main__':
    app.run(debug=True)