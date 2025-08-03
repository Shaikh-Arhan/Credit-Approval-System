🏦 Credit Approval System API

![Django] (https://img.shields.io/badge/Django-4.0-green)
![PostgreSQL] (https://img.shields.io/badge/PostgreSQL-13-blue)
![Docker] (https://img.shields.io/badge/Docker-Compose-orange)

A REST API for automating loan eligibility decisions with:
- Customer risk profiling
- Loan approval automation
- Historical data analysis
- Excel data integration

📦 Prerequisites

- Docker Desktop 
- Python 3.9+ (for manual setup)
- PostgreSQL 13+ (for manual setup)

🚀 Quick Start (Docker)

- bash
1. Clone repository
git clone https://github.com/Shaikh-Arhan/credit-approval-system.git
cd credit-approval-system

2. Add data files (see Data section)
cp /path/to/customer_data.xlsx data/
cp /path/to/loan_data.xlsx data/

3. Start services
docker-compose up --build -d

4. Initialize database
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py ingest_data

5. Access API at:
curl http://localhost:8000/api/register/

🔧 Manual Setup

- Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate  # Windows

- Install dependencies
pip install -r requirements.txt

- Configure PostgreSQL (create DB first)
export DATABASE_URL="postgres://user:pass@localhost:5432/credit_db"

- Run migrations
python manage.py migrate
python manage.py ingest_data
python manage.py runserver

📚 API Documentation
Endpoints
Endpoint	                 Method	      Description
/api/register/	               POST	    Register new customer
/api/check-eligibility/	       POST	    Loan eligibility check
/api/create-loan/	           POST     Process new loan
/api/view-loan/<loan_id>/   	GET     Loan details
/api/view-loans/<customer_id>/	GET     Customer's loan history

🛠️ Admin Access
- Create superuser
docker-compose exec web python manage.py createsuperuser
- Access admin panel:
http://localhost:8000/admin

Developed by Shaikh Arhan.


