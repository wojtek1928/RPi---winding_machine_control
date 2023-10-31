CREATE TABLE orders (
    order_id TEXT PRIMARY KEY UNIQUE NOT NULL,
    status TEXT CHECK( status IN ('TODO','DONE','INTERRUPTED')) NOT NULL DEFAULT 'TODO',
    customer_name TEXT DEFAULT NULL,
    quantity INTEGER NOT NULL,
    length INTEGER NOT NULL,
    diameter REAL NOT NULL,
    production_time INTEGER DEFAULT NULL,
    done_date DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);