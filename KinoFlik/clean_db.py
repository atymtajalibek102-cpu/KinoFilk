import sqlite3

def clean_database():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    queries = [
        "DELETE FROM movies WHERE genre LIKE '%аниме%' OR genre LIKE '%anime%' OR age_rating='18+' OR age_rating='18' OR genre LIKE '%эротика%'",
        "DELETE FROM series WHERE genre LIKE '%аниме%' OR genre LIKE '%anime%' OR genre LIKE '%эротика%'"
    ]
    
    for q in queries:
        c.execute(q)
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    clean_database()
