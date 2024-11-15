
from flask import Flask, jsonify, render_template, request, redirect, g, url_for, session
import mysql.connector
from flask_bcrypt import Bcrypt
import re
import logging
from datetime import timedelta

from functools import wraps

EMAIL_PATTERN = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')

app = Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SECRET_KEY'] = 'your_secret_key'
bcrypt = Bcrypt(app)

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
            LIMIT 45
        """
        cursor.execute(movies_query)
        movies = cursor.fetchall()

        return render_template('index.html',
                             movies=movies,
                             genres=genres,
                             user=session.get('username'))
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('index.html', error="An error occurred while searching movies")


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
                return render_template('index.html', error="Invalid minimum rating")
            if max_rating and not validate_rating(max_rating):
                return render_template('index.html', error="Invalid maximum rating")

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
        return render_template('index.html', error="An error occurred while searching movies")


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
            return render_template('index.html', error="Invalid minimum rating")
        if search_params['max_rating'] and not validate_rating(search_params['max_rating']):
            return render_template('index.html', error="Invalid maximum rating")

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
        return render_template('index.html', error="An error occurred while searching movies")


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
    return render_template('index.html', error="Page not found"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('index.html', error="Internal server error"), 500


# Add these new routes to your existing Python file

@app.route('/dashboard')
# @login_required  # This ensures only logged-in users can access
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
                               genres=genres,
                               username=session.get('username'))
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return redirect(url_for('index'))


# Add to app.py
@app.route('/load_more')
def load_more():
    page = int(request.args.get('page', 1))
    limit = 45
    offset = (page - 1) * limit

    try:
        db, cursor = get_db()
        query = """
            SELECT DISTINCT
                m.ID, m.Title, ROUND(r.Rating, 1) as Rating,
                m.Runtime, GROUP_CONCAT(DISTINCT g.GenreName) as Genres,
                m.Metascore, m.Plot,
                GROUP_CONCAT(DISTINCT d.DirectorName) as Directors,
                GROUP_CONCAT(DISTINCT s.StarName) as Stars,
                r.Votes, CONCAT('$', FORMAT(m.Gross, 2)) as Gross,
                m.Link
            FROM Movies m
            LEFT JOIN Ratings r ON m.ID = r.MovieID
            LEFT JOIN MovieGenres mg ON m.ID = mg.MovieID
            LEFT JOIN Genres g ON mg.GenreID = g.GenreID
            LEFT JOIN MovieDirectors md ON m.ID = md.MovieID
            LEFT JOIN Directors d ON md.DirectorID = d.DirectorID
            LEFT JOIN MovieStars ms ON m.ID = ms.MovieID
            LEFT JOIN Stars s ON ms.StarID = s.StarID
            GROUP BY m.ID
            ORDER BY r.Rating DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (limit, offset))
        movies = cursor.fetchall()

        # Check if there are more movies
        cursor.execute("SELECT COUNT(*) FROM Movies")
        total = cursor.fetchone()[0]
        has_more = (offset + limit) < total

        return jsonify({
            'movies': movies,
            'hasMore': has_more
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)