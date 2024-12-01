import csv
import mysql.connector

# Database connection details
db_config = {
    'host': 'cse335-fall-2024.c924km8o85q2.us-east-1.rds.amazonaws.com',
    'user': 'v0igir01',
    'password': '2c3e13850d',
    'database': 'student_v0igir01_db'
}

# Establish database connection
connection = mysql.connector.connect(**db_config)
cursor = connection.cursor()

# Create the moviese table if it doesn't exist
create_table_query = """
CREATE TABLE IF NOT EXISTS moviese (
    ID INT PRIMARY KEY,
    Movie_Name VARCHAR(255),
    Rating FLOAT,
    Runtime INT,
    Genre VARCHAR(255),
    Metascore INT,
    Plot TEXT,
    Directors VARCHAR(255),
    Stars VARCHAR(255),
    Votes INT,
    Gross FLOAT,
    Link VARCHAR(255)
);
"""
cursor.execute(create_table_query)

# CSV file path
csv_file_path = 'Top_10000_Movies_IMDb.csv'

# Insert data from CSV into the moviese table
with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
    csv_reader = csv.DictReader(csvfile)
    insert_query = """
    INSERT INTO moviese (ID, Movie_Name, Rating, Runtime, Genre, Metascore, Plot, Directors, Stars, Votes, Gross, Link)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    for row in csv_reader:
        cursor.execute(insert_query, (
            row['ID'], row['Movie Name'], row['Rating'], row['Runtime'],
            row['Genre'], row['Metascore'], row['Plot'], row['Directors'],
            row['Stars'], row['Votes'], row['Gross'], row['Link']
        ))

# Commit changes and close the connection
connection.commit()
cursor.close()
connection.close()

print("Data inserted successfully!")
if __name__ == '__main__':
    pass
