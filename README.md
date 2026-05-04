# Freight & Logistics Management System

## Overview
A Flask and MySQL freight logistics system with role-based access for admins, couriers, and customers. The app supports parcel tracking, courier management, dashboard analytics, and parcel condition history.

## Main Features
- Admin dashboard for parcel and courier management
- Courier dashboard for assigned deliveries and condition updates
- Customer registration and login
- Parcel CRUD operations and courier assignment
- Analytics charts for parcel status, trends, and courier performance
- Parcel condition tracking with audit logs
- bcrypt password hashing and session-based authentication

## Tech Stack
- Backend: Flask, Python
- Database: MySQL
- Frontend: HTML, CSS, Bootstrap, Chart.js
- Authentication: bcrypt
- Environment management: python-dotenv

## Requirements
- Python 3.8 or newer
- MySQL 8.0 or newer
- Windows PowerShell or Command Prompt

## How To Run

### 1. Open the project folder
Open a terminal in this directory:
```bash
cd freight-logistics
```

### 2. Create and activate a virtual environment
On Windows PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, allow it for the current session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create the database
Import the schema into MySQL:
```bash
mysql -u root -p < database_schema.sql
```

You can also run the SQL in MySQL Workbench or another MySQL client using [database_schema.sql](database_schema.sql).

### 5. Configure the environment
Create or edit the `.env` file in the project root:
```env
SECRET_KEY=your-secret-key
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=freight_logistics
```

### 6. Start the app
Run the Flask app directly:
```bash
python app.py
```

Open:
```text
http://127.0.0.1:5000
```

## Default Login Accounts

| Role | Username | Password |
| --- | --- | --- |
| Admin | admin | admin123 |
| Courier | courier1 | courier123 |

## What The App Does
Admins can review dashboard analytics, manage parcels, assign couriers, and monitor delivery performance. Couriers can see assigned parcels, open parcel details, and update parcel conditions. Customers can register, log in, and use the customer-facing parcel pages.

## Database Notes
The project uses MySQL tables for users, parcels, parcel assignments, parcel conditions, and audit logs. Connection settings are loaded from `.env` when `app.py` starts.

## Project Files
The main runtime files are `app.py`, `database_schema.sql`, `requirements.txt`, `templates/`, and `static/`. A zipped backup copy is also present in the repository as `freight-logistics.zip`.

## Important Notes
- The app is started with `python app.py`; no separate runtime script is required.
- Helper setup scripts were removed from the working tree, so the README now reflects the current app-first workflow.
- If MySQL cannot connect, verify the `.env` values and confirm the database exists before starting the app.

## Testing Checklist

- [ ] Database created and seeded with 2000 parcels
- [ ] Admin login works (admin/admin123)
- [ ] Courier login works (courier1/admin123)
- [ ] Landing page displays with marketing content
- [ ] Admin dashboard loads with all charts
- [ ] Can view and filter parcels
- [ ] Can edit parcel details
- [ ] Can assign parcels to couriers
- [ ] Courier can view assigned parcels
- [ ] Courier can update parcel condition
- [ ] Condition history displays correctly
- [ ] Auto-cancellation scheduler works
- [ ] Analytics update in real-time

## Troubleshooting

### Database Connection Error
```
Error connecting to MySQL
```
**Solution**: Check `.env` file for correct credentials and ensure MySQL is running.

### Port Already in Use
```
Address already in use
```
**Solution**: Change port in `app.py` (last line) or kill the process using port 5000.

### Module Not Found
```
ModuleNotFoundError: No module named 'flask'
```
**Solution**: Ensure virtual environment is activated and dependencies installed.

### Seed Script Fails
```
ERROR: No couriers found
```
**Solution**: Ensure database schema is imported before running seed script.

## Future Enhancements

- Mobile app (React Native/Flutter)
- Real-time notifications (Firebase Cloud Messaging)
- GPS tracking with map integration
- Email notifications for status changes
- Advanced route optimization
- Payment gateway integration
- Advanced reporting and exports
- Machine learning for delivery time predictions

## Support

For issues or questions, check the logs in the terminal or enable Flask debug mode in `.env`:
```
FLASK_DEBUG=True
```

## License

This project is for educational purposes.

---

**Version**: 1.0  
**Last Updated**: 2026 
**Status**: Production Ready
