from sqlalchemy import text
from db.connection import get_db

db = next(get_db())
result = db.execute(text("SELECT column_name, is_nullable, data_type FROM information_schema.columns WHERE table_name = 'videos' ORDER BY ordinal_position;"))
columns = result.fetchall()

print('Videos table columns:')
for col in columns:
    nullable = "NULL" if col[1] == "YES" else "NOT NULL"
    print(f'  {col[0]} - {col[2]} - {nullable}')

db.close()