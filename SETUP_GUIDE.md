# Freight Logistics - Setup & Installation Guide

## Quick Start (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up database (in MySQL)
mysql -u root -p < freight_logistics.sql
mysql -u root -p < extended_schema.sql

# 3. Run the application
python app_secure.py

# 4. Open browser
# Navigate to http://localhost:5000
# Login: admin / admin123
```

---

## Detailed Installation Guide

### Prerequisites

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- MySQL running on localhost:3306

### Step 1: Environment Setup

#### Windows (PowerShell)
```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

#### macOS/Linux (Bash)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Setup

#### Option A: Using MySQL CLI

```bash
# Connect to MySQL
mysql -u root -p

# In MySQL prompt:
CREATE DATABASE IF NOT EXISTS freight_logistics;
USE freight_logistics;
SOURCE freight_logistics.sql;
SOURCE extended_schema.sql;
EXIT;
```

#### Option B: Using MySQL Workbench

1. Open MySQL Workbench
2. Create new connection (localhost:3306)
3. Execute `freight_logistics.sql`
4. Execute `extended_schema.sql`

#### Option C: Using phpMyAdmin

1. Open phpMyAdmin
2. Create database: `freight_logistics`
3. Import `freight_logistics.sql`
4. Import `extended_schema.sql`

### Step 3: Verify Database

```bash
mysql -u root -p freight_logistics -e "SELECT COUNT(*) as table_count FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'freight_logistics';"
```

Expected output: Should show at least 7 tables

### Step 4: Run Application

```bash
python app_secure.py
```

Expected output:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### Step 5: Access the System

1. Open web browser
2. Navigate to: `http://localhost:5000`
3. Login with default credentials:
   - **Username**: admin
   - **Password**: admin123

---

## User Roles & Permissions

### 1. Admin Role

**Permissions**:
- ✓ Create new shipments
- ✓ Edit shipment status
- ✓ View all shipments
- ✓ Assign shipments to riders
- ✓ Manage riders (activate/deactivate)
- ✓ View delivery statistics
- ✓ Access audit logs

**Access Routes**:
- `/dashboard` - Admin dashboard
- `/shipments` - All shipments
- `/shipment/new` - Create shipment
- `/shipment/<id>/edit` - Edit shipment
- `/admin/riders` - Manage riders
- `/admin/assign-shipment` - Assign shipment to rider
- `/admin/statistics` - View statistics

### 2. Rider Role

**Permissions**:
- ✓ View only assigned shipments
- ✓ Update tracking information
- ✓ View shipment details
- ✗ Cannot create shipments
- ✗ Cannot assign to other riders
- ✗ Cannot manage users

**Access Routes**:
- `/dashboard` - Rider dashboard
- `/shipments` - My assigned shipments
- `/shipment/<id>/tracking` - View tracking

### 3. User Role

**Permissions**:
- ✓ Same as Rider
- ✓ Register account
- ✗ No admin functions

---

## Common Workflows

### Workflow A: Admin Creating & Assigning Shipment

1. **Login as Admin**
   - Navigate to http://localhost:5000
   - Username: `admin`
   - Password: `admin123`

2. **Create New Shipment**
   - Click "New Shipment" or navigate to `/shipment/new`
   - Fill in fields:
     - Reference Number: `SHIP001`
     - Origin: `Manila, Philippines`
     - Destination: `Cebu, Philippines`
     - Weight: `50`
   - Click "Create"

3. **Assign to Rider**
   - Go to Admin → Assign Shipment
   - Select the shipment from dropdown
   - Select a rider
   - Add notes (optional): "Priority delivery"
   - Click "Assign Shipment"

4. **Monitor Delivery**
   - View shipment in `/shipments`
   - Status: Pending → In Transit → Delivered

### Workflow B: Rider Registration & Receiving Shipments

1. **Register as Rider**
   - Navigate to http://localhost:5000/register
   - Fill form:
     - Full Name: `Juan Santos`
     - Username: `juan_santos`
     - Email: `juan@example.com`
     - Phone: `09171234567`
     - Password: `SecurePass123`
   - Click "Create Account"

2. **Login as Rider**
   - Use credentials just created
   - View dashboard
   - See "My Assignments"

3. **View Assigned Shipments**
   - Click "View Shipments"
   - See only your assignments
   - Click shipment for details

4. **Track Shipment**
   - Click on shipment
   - View GPS tracking route
   - View delivery details

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```env
# Flask
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key-here

# MySQL
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=freight_logistics

# Security
SESSION_SECURE=False  # Set to True with HTTPS in production
```

### Security Best Practices

1. **Change Admin Password Immediately**
   ```bash
   # In production, create new admin user and delete default
   ```

2. **Use HTTPS in Production**
   ```python
   # In app.py
   app.config["SESSION_COOKIE_SECURE"] = True
   app.config["SESSION_COOKIE_HTTPONLY"] = True
   ```

3. **Update SECRET_KEY**
   ```bash
   # Generate new secret
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Database User Privileges**
   ```sql
   -- Create app-specific user (not root)
   CREATE USER 'freight_app'@'localhost' IDENTIFIED BY 'strong_password';
   GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON freight_logistics.* 
   TO 'freight_app'@'localhost';
   ```

---

## Database Schema Overview

### Tables Created

| Table | Purpose |
|-------|---------|
| shipments | Main shipment records |
| gps_sessions | GPS tracking sessions |
| gps_pings | Individual GPS location points |
| users | User accounts with roles |
| user_sessions | Active user sessions |
| shipment_assignments | Rider-Shipment assignments (N:M) |
| audit_logs | Audit trail of all actions |

### Stored Procedures

| Procedure | Purpose |
|-----------|---------|
| GetUserShipments | Role-based shipment visibility |
| AssignShipmentToRider | Transactional assignment with logging |
| GetDeliveryStatistics | Dashboard metrics calculation |
| GetRiderPerformance | Rider KPI metrics |

---

## Testing the System

### Test 1: Login System
```
1. Go to http://localhost:5000/login
2. Try with wrong credentials → should fail
3. Try with admin/admin123 → should succeed
4. Verify session created (check browser cookies)
```

### Test 2: Role-Based Access
```
1. Login as admin
2. Access /admin/riders → should work
3. Logout
4. Register new account as rider
5. Login as rider
6. Try accessing /admin/riders → should be denied
```

### Test 3: Shipment Visibility
```
1. Login as admin
2. Create new shipment
3. Go to /shipments → see shipment with "No riders" or "Unassigned"
4. Assign to a rider via /admin/assign-shipment
5. Logout
6. Login as that rider
7. Go to /shipments → should see only assigned shipment
```

### Test 4: Audit Logging
```
1. Perform actions (login, create shipment, assign)
2. Check audit_logs table:
   SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;
3. Verify all actions are logged with timestamps and IP
```

### Test 5: Stored Procedures
```
-- Get shipments for admin
CALL GetUserShipments(1, 'admin');

-- Get shipments for rider
CALL GetUserShipments(2, 'rider');

-- Get delivery statistics
CALL GetDeliveryStatistics('2024-01-01', CURDATE());

-- Get rider performance
CALL GetRiderPerformance(2, 30);
```

---

## Troubleshooting

### Issue: "Unable to connect to database"

**Solution 1**: Check MySQL is running
```bash
# Windows
Get-Service MySQL*  # Or 'mysql' depending on installation

# macOS
brew services list

# Linux
sudo service mysql status
```

**Solution 2**: Verify credentials in app_secure.py
```python
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Empty if no password
    "database": "freight_logistics"
}
```

**Solution 3**: Check database exists
```bash
mysql -u root -p -e "SHOW DATABASES;"
```

### Issue: "ModuleNotFoundError: No module named 'bcrypt'"

**Solution**: Install requirements
```bash
pip install -r requirements.txt
```

### Issue: "1054 Unknown column 'users.id' in foreign key constraint"

**Solution**: Run extended_schema.sql
```bash
mysql -u root -p freight_logistics < extended_schema.sql
```

### Issue: "Session expires too quickly"

**Solution**: Adjust session timeout
```python
# In app_secure.py
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=4)
```

### Issue: "Port 5000 already in use"

**Solution**: Use different port
```bash
python app_secure.py --port 5001
```

Or modify app.py:
```python
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Change admin password
- [ ] Update SECRET_KEY
- [ ] Set FLASK_ENV=production
- [ ] Enable HTTPS/SSL certificates
- [ ] Set SESSION_COOKIE_SECURE=True
- [ ] Create database backup
- [ ] Test all workflows
- [ ] Review audit logs
- [ ] Set up error logging
- [ ] Configure firewall rules

### Deployment Steps

1. **Install on Server**
   ```bash
   cd /var/www/freight-logistics
   git clone <repo-url> .
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Gunicorn**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app_secure:app
   ```

3. **Setup Nginx Reverse Proxy**
   ```nginx
   server {
       listen 80;
       server_name logistics.example.com;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
       }
   }
   ```

4. **Enable SSL with Let's Encrypt**
   ```bash
   certbot --nginx -d logistics.example.com
   ```

5. **Setup Database Backups**
   ```bash
   # Daily backup cron job
   0 2 * * * mysqldump -u freight_app -p freight_logistics > /backups/freight_logistics_$(date +\%Y\%m\%d).sql
   ```

---

## Support & Documentation

### Files Included

- `app_secure.py` - Main Flask application
- `extended_schema.sql` - Database schema with procedures
- `requirements.txt` - Python dependencies
- `DATABASE_NORMALIZATION.md` - Schema documentation
- `SETUP_GUIDE.md` - This file
- `templates/` - HTML templates
- `static/` - CSS and JavaScript

### Additional Resources

- Flask Documentation: https://flask.palletsprojects.com/
- MySQL Documentation: https://dev.mysql.com/doc/
- Bcrypt: https://github.com/pyca/bcrypt

---

## Next Steps

1. ✅ Complete initial setup
2. ✅ Test all user workflows
3. ✅ Customize templates (branding)
4. ✅ Configure email notifications (optional)
5. ✅ Set up monitoring and alerts
6. ✅ Plan backup strategy
7. ✅ Document your customizations
8. ✅ Deploy to production

---

**Last Updated**: April 2026
**Version**: 1.0
**Status**: Production Ready
