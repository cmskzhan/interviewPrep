import csv
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, Text, select, insert, func,
)

engine = create_engine('sqlite:///market_data.db', echo=True)
metadata = MetaData()

# Reflect the existing stock_bars table from the database
metadata.reflect(bind=engine)
stock_bars = metadata.tables['stock_bars']

with engine.connect() as conn:
    result = conn.execute(select(stock_bars))
    for row in result:
        print(row)

# --- Define traders table (user_id AUTOINCREMENT) ---
traders = Table(
    'traders', metadata,
    Column('user_id',   Integer, primary_key=True, autoincrement=True),
    Column('firstname', Text, nullable=False),
    Column('lastname',  Text, nullable=False),
    Column('email',     Text, nullable=False),
    Column('band',      Integer, nullable=True),
    extend_existing=True,
)

# Create table if it doesn't exist
metadata.create_all(engine, tables=[traders])

# --- Load from CSV and insert ---
with engine.connect() as conn:
    row_count = conn.execute(select(func.count()).select_from(traders)).scalar_one()

    with open('traders.csv', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                insert(traders).values(
                    firstname=row['firstname'],
                    lastname=row['lastname'],
                    email=row['email'],
                    band=int(row['band']),
                )
            )
    conn.commit()
    new_row_count = conn.execute(select(func.count()).select_from(traders)).scalar_one()
    print(f"Inserted {new_row_count - row_count} rows from traders.csv")

    result = conn.execute(select(traders))
    print("\n--- traders table ---")
    for row in result:
        print(row)


