# FreightFlow PH - MySQL Conversion Setup

You now have everything to convert your freight logistics system from SQLite to MySQL/phpMyAdmin!

## What You Get

This package includes:

1. **app_mysql.py** — Flask app configured for MySQL (drop-in replacement for app.py)
2. **MYSQL_SETUP.md** — SQL commands to create the database schema in MySQL
3. **migrate_to_mysql.py** — Python script to migrate all your data from SQLite to MySQL
4. **MYSQL_CONVERSION.md** — Complete step-by-step guide

## Quick Start (3 Steps)

### Step 1: Install MySQL Driver
```bash
pip install mysql-connector-python
```

### Step 2: Create MySQL Database
Open **phpMyAdmin** at `http://localhost/phpmyadmin`
- Login (username: `root`, password: leave empty)
- Click **New** on the left
- Create database: `freight_logistics`
- In the database, click **SQL** tab
- Copy-paste all commands from `MYSQL_SETUP.md`
- Click **Go**

### Step 3: Migrate Your Data (Optional)
If you have existing data in SQLite:
```bash
python migrate_to_mysql.py
```

This copies all 2000+ shipments, GPS data, and tracking history to MySQL.

## Running the App

**Option A: Keep using SQLite** (current setup)
```bash
python app.py
```

**Option B: Use MySQL** (new setup)
```bash
python app_mysql.py
```

Or rename:
```bash
copy app.py app_sqlite.py
copy app_mysql.py app.py
python app.py
```

## Why Convert to MySQL?

| Feature | SQLite | MySQL |
|---------|--------|-------|
| **Web Interface** | None | phpMyAdmin ✓ |
| **Real-Time Data Browse** | File-based | Live dashboard |
| **Backups** | Manual file copy | Automated dumps |
| **Multi-User Access** | Limited | Full support ✓ |
| **Query Performance** | OK | Optimized ✓ |
| **Scalability** | Single file limit | Unlimited ✓ |

## File Overview

```
SemProjCodes/
├── app.py                    (SQLite version - keep as backup)
├── app_mysql.py             (MySQL version - new)
├── migrate_to_mysql.py      (Data migration script)
├── MYSQL_SETUP.md           (Database schema SQL)
├── MYSQL_CONVERSION.md      (Full guide - READ THIS!)
├── freight_logistics.db     (SQLite database - will stay)
├── templates/               (HTML templates - unchanged)
├── static/                  (CSS/JS - unchanged)
└── requirements.txt         (Updated with mysql-connector-python)
```

## Connection Details

**For MySQL (XAMPP default):**
- Host: `localhost`
- Port: `3306`
- User: `root`
- Password: (empty)
- Database: `freight_logistics`

**phpMyAdmin URL:**
```
http://localhost/phpmyadmin
```

## Support

If you encounter issues:

1. **MySQL won't connect:**
   - Ensure XAMPP MySQL service is running
   - Check phpMyAdmin works: `http://localhost/phpmyadmin`

2. **Database not found:**
   - Run MYSQL_SETUP.md SQL in phpMyAdmin
   - Check database name is `freight_logistics`

3. **Data migration fails:**
   - Ensure SQLite database exists: `freight_logistics.db`
   - Verify MySQL database is empty before migrating
   - Run `migrate_to_mysql.py` from project root

4. **Port conflicts:**
   - MySQL default is 3306
   - Verify XAMPP isn't using conflicting ports

## Next Steps

1. Read **MYSQL_CONVERSION.md** for detailed setup
2. Review **MYSQL_SETUP.md** for the database schema
3. Run **migrate_to_mysql.py** to move your 2000+ records
4. Test with `python app_mysql.py`
5. Access phpMyAdmin to manage data graphically

**Enjoy your new MySQL-powered freight logistics system!** 🚀
