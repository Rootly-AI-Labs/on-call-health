# Database Migration Notes

## Changes Made to Analysis Model

The `Analysis` model has been updated to include a new `time_range` field:

### New Field Added:
```python
time_range = Column(Integer, default=30)  # Time range in days
```

### Migration Required

If you're using an existing database, you'll need to add the new column. Here's the SQL to add it:

```sql
ALTER TABLE analyses ADD COLUMN time_range INTEGER DEFAULT 30;
```

### Background

Previously, the `time_range` was stored in the `config` JSON field. Now it's a dedicated column for:
- Better query performance
- Easier filtering and indexing
- Cleaner API responses
- More consistent data structure

### Compatibility

The new endpoints will work with both:
- New analyses (using the `time_range` column)
- Legacy analyses (falling back to `config.time_range` or default 30)

The response handling includes backward compatibility:
```python
time_range=analysis.time_range or 30
```

### Full Schema

Current `analyses` table structure:
```sql
CREATE TABLE analyses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    rootly_integration_id INTEGER,
    time_range INTEGER DEFAULT 30,
    status VARCHAR(50) DEFAULT 'pending',
    config JSON,
    results JSON,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (rootly_integration_id) REFERENCES rootly_integrations(id)
);
```