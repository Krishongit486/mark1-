# main.py
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from datetime import date, timedelta
import datetime
import csv
import io
import os
import secrets
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
from database import get_db, Base, engine
import models
import schemas
from starlette_prometheus import metrics, PrometheusMiddleware
from sklearn.linear_model import LinearRegression
import pandas as pd
from sqlalchemy import func

# --- Application Initialization ---
app = FastAPI(
    title="eArbor IoT Data Platform",
    description="Backend for processing IoT data, managing personnel, and providing analytics.",
    version="1.0.0"
)

# Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

# Initialize database
Base.metadata.create_all(bind=engine)

# Serve static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# --- Configuration for JWT Authentication ---
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Utility Functions for Security ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_active_admin(current_user: models.User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an administrator")
    return current_user

# --- Authentication and User Management Endpoints ---
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user_username = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/me/", response_model=schemas.UserOut)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@app.get("/users/{user_id}", response_model=schemas.UserOut)
async def read_user_by_id(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users/", response_model=List[schemas.UserOut])
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

# --- Employee Management Endpoints ---
@app.post("/employees/", response_model=schemas.EmployeeOut)
async def create_employee(employee: schemas.EmployeeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    db_employee = db.query(models.Employee).filter(models.Employee.email == employee.email).first()
    if db_employee:
        raise HTTPException(status_code=400, detail="Employee with this email already exists")
    new_employee = models.Employee(**employee.model_dump())
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

@app.get("/employees/", response_model=List[schemas.EmployeeOut])
async def read_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    employees = db.query(models.Employee).filter(models.Employee.is_active == True).offset(skip).limit(limit).all()
    return employees

@app.get("/employees/{employee_id}", response_model=schemas.EmployeeOutWithDocuments)
async def read_employee(employee_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@app.put("/employees/{employee_id}", response_model=schemas.EmployeeOut)
async def update_employee(employee_id: int, employee_update: schemas.EmployeeUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    update_data = employee_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_employee, key, value)
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

@app.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_employee(employee_id: int, reason: Optional[str] = "Deactivated", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    archived_employee = models.ArchivedEmployee(
        original_id=db_employee.id,
        first_name=db_employee.first_name,
        last_name=db_employee.last_name,
        email=db_employee.email,
        phone_number=db_employee.phone_number,
        position=db_employee.position,
        is_active=False,
        registration_date=db_employee.registration_date,
        archive_date=datetime.date.today(),
        archived_reason=reason
    )
    db.add(archived_employee)
    db.delete(db_employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Trucker Management Endpoints ---
@app.post("/truckers/", response_model=schemas.TruckerOut)
async def create_trucker(trucker: schemas.TruckerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    if trucker.email:
        db_trucker_email = db.query(models.Trucker).filter(models.Trucker.email == trucker.email).first()
        if db_trucker_email:
            raise HTTPException(status_code=400, detail="Trucker with this email already exists")
    db_trucker_license = db.query(models.Trucker).filter(models.Trucker.driver_license_number == trucker.driver_license_number).first()
    if db_trucker_license:
        raise HTTPException(status_code=400, detail="Trucker with this driver license number already exists")
    if trucker.truck_id_number:
        db_trucker_truck_id = db.query(models.Trucker).filter(models.Trucker.truck_id_number == trucker.truck_id_number).first()
        if db_trucker_truck_id:
            raise HTTPException(status_code=400, detail="Trucker with this truck ID number already exists")
    new_trucker = models.Trucker(**trucker.model_dump())
    db.add(new_trucker)
    db.commit()
    db.refresh(new_trucker)
    return new_trucker

@app.get("/truckers/", response_model=List[schemas.TruckerOut])
async def read_truckers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    truckers = db.query(models.Trucker).filter(models.Trucker.is_active == True).offset(skip).limit(limit).all()
    return truckers

@app.get("/truckers/{trucker_id}", response_model=schemas.TruckerOutWithDocuments)
async def read_trucker(trucker_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if not trucker:
        raise HTTPException(status_code=404, detail="Trucker not found")
    return trucker

@app.put("/truckers/{trucker_id}", response_model=schemas.TruckerOut)
async def update_trucker(trucker_id: int, trucker_update: schemas.TruckerUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    db_trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if not db_trucker:
        raise HTTPException(status_code=404, detail="Trucker not found")
    update_data = trucker_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_trucker, key, value)
    db.add(db_trucker)
    db.commit()
    db.refresh(db_trucker)
    return db_trucker

@app.delete("/truckers/{trucker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_trucker(trucker_id: int, reason: Optional[str] = "Deactivated", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    db_trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if not db_trucker:
        raise HTTPException(status_code=404, detail="Trucker not found")
    archived_trucker = models.ArchivedTrucker(
        original_id=db_trucker.id,
        first_name=db_trucker.first_name,
        last_name=db_trucker.last_name,
        email=db_trucker.email,
        phone_number=db_trucker.phone_number,
        driver_license_number=db_trucker.driver_license_number,
        province_of_issue=db_trucker.province_of_issue,
        truck_id_number=db_trucker.truck_id_number,
        company_name=db_trucker.company_name,
        is_active=False,
        registration_date=db_trucker.registration_date,
        archive_date=datetime.date.today(),
        archived_reason=reason
    )
    db.add(archived_trucker)
    db.delete(db_trucker)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Document Management Endpoints ---
@app.post("/documents/", response_model=schemas.DocumentOut)
async def create_document(document: schemas.DocumentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if document.employee_id:
        employee = db.query(models.Employee).filter(models.Employee.id == document.employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
    if document.trucker_id:
        trucker = db.query(models.Trucker).filter(models.Trucker.id == document.trucker_id).first()
        if not trucker:
            raise HTTPException(status_code=404, detail="Trucker not found")
    new_document = models.Document(**document.model_dump())
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    return new_document

@app.get("/documents/", response_model=List[schemas.DocumentOut])
async def read_documents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    documents = db.query(models.Document).offset(skip).limit(limit).all()
    return documents

@app.get("/documents/{document_id}", response_model=schemas.DocumentOut)
async def read_document(document_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@app.put("/documents/{document_id}", response_model=schemas.DocumentOut)
async def update_document(document_id: int, document_update: schemas.DocumentUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    update_data = document_update.model_dump(exclude_unset=True)
    if "is_verified" in update_data:
        if update_data["is_verified"] and db_document.verification_date is None:
            db_document.verification_date = datetime.date.today()
        elif not update_data["is_verified"]:
            db_document.verification_date = None
            db_document.verified_by = None
    for key, value in update_data.items():
        setattr(db_document, key, value)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_document(document_id: int, reason: Optional[str] = "Deactivated", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    archived_document = models.ArchivedDocument(
        original_id=db_document.id,
        document_type=db_document.document_type,
        file_path=db_document.file_path,
        upload_date=db_document.upload_date,
        is_verified=db_document.is_verified,
        verification_date=db_document.verification_date,
        verified_by=db_document.verified_by,
        employee_id=db_document.employee_id,
        trucker_id=db_document.trucker_id,
        archive_date=datetime.date.today(),
        archived_reason=reason
    )
    db.add(archived_document)
    db.delete(db_document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Search and Analytics Endpoints ---
@app.get("/search/", response_model=List[schemas.LiveSearchResult])
async def live_search(query: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    search_results = []
    employees = db.query(models.Employee).filter(
        models.Employee.is_active == True,
        (models.Employee.first_name.ilike(f"%{query}%")) |
        (models.Employee.last_name.ilike(f"%{query}%")) |
        (models.Employee.email.ilike(f"%{query}%"))
    ).limit(10).all()
    for emp in employees:
        search_results.append(schemas.LiveSearchResult(
            type="employee",
            id=emp.id,
            name=f"{emp.first_name} {emp.last_name}",
            identifier=emp.email,
            is_active=emp.is_active,
            details=schemas.EmployeeOut.model_validate(emp)
        ))
    truckers = db.query(models.Trucker).filter(
        models.Trucker.is_active == True,
        (models.Trucker.first_name.ilike(f"%{query}%")) |
        (models.Trucker.last_name.ilike(f"%{query}%")) |
        (models.Trucker.email.ilike(f"%{query}%")) |
        (models.Trucker.driver_license_number.ilike(f"%{query}%")) |
        (models.Trucker.truck_id_number.ilike(f"%{query}%"))
    ).limit(10).all()
    for trk in truckers:
        search_results.append(schemas.LiveSearchResult(
            type="trucker",
            id=trk.id,
            name=f"{trk.first_name} {trk.last_name}",
            identifier=trk.driver_license_number,
            is_active=trk.is_active,
            details=schemas.TruckerOut.model_validate(trk)
        ))
    return search_results

@app.get("/compliance-data", response_model=schemas.ComplianceData)
async def get_compliance_data(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    total_employees = db.query(models.Employee).count()
    active_employees = db.query(models.Employee).filter(models.Employee.is_active == True).count()
    total_truckers = db.query(models.Trucker).count()
    active_truckers = db.query(models.Trucker).filter(models.Trucker.is_active == True).count()
    documents_uploaded = db.query(models.Document).count()
    documents_verified = db.query(models.Document).filter(models.Document.is_verified == True).count()
    unverified_documents = documents_uploaded - documents_verified
    return schemas.ComplianceData(
        total_employees=total_employees,
        active_employees=active_employees,
        total_truckers=total_truckers,
        active_truckers=active_truckers,
        documents_uploaded=documents_uploaded,
        documents_verified=documents_verified,
        unverified_documents=unverified_documents
    )

@app.get("/analytics/employee-growth", response_model=schemas.EmployeeGrowthAnalysis)
async def get_employee_growth(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    employee_growth_data = db.query(
        models.Employee.registration_date,
        func.count(models.Employee.id)
    ).group_by(
        func.strftime('%Y-%m', models.Employee.registration_date)
    ).order_by(
        models.Employee.registration_date
    ).all()
    monthly_growth = [schemas.RegistrationGrowth(date=str(reg_date), count=count) for reg_date, count in employee_growth_data]
    total_employees = db.query(models.Employee).count()
    average_monthly_growth = sum(item.count for item in monthly_growth) / len(monthly_growth) if monthly_growth else 0.0
    projected_next_month = None
    if len(monthly_growth) >= 2:
        X = [[i] for i in range(len(monthly_growth))]
        y = [item.count for item in monthly_growth]
        model = LinearRegression()
        model.fit(X, y)
        projected_next_month_val = model.predict([[len(monthly_growth)]])[0]
        projected_next_month = max(0, int(projected_next_month_val))
    return schemas.EmployeeGrowthAnalysis(
        monthly_growth=monthly_growth,
        total_employees=total_employees,
        average_monthly_growth=average_monthly_growth,
        projected_next_month=projected_next_month
    )

@app.get("/analytics/trucker-distribution", response_model=schemas.TruckerAnalysis)
async def get_trucker_distribution(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    province_counts = db.query(models.Trucker.province_of_issue, func.count(models.Trucker.id)).group_by(models.Trucker.province_of_issue).all()
    province_distribution = {prov: count for prov, count in province_counts}
    company_counts = db.query(func.coalesce(models.Trucker.company_name, 'Independent'), func.count(models.Trucker.id)).group_by(func.coalesce(models.Trucker.company_name, 'Independent')).all()
    total_truckers = db.query(models.Trucker).count()
    company_distribution = []
    most_common_type = None
    max_count = 0
    for company, count in company_counts:
        percentage = (count / total_truckers) * 100 if total_truckers > 0 else 0.0
        company_distribution.append(schemas.TruckerTypeDistribution(company_name=company, count=count, percentage=round(percentage, 2)))
        if count > max_count:
            max_count = count
            most_common_type = company
    predictive_trend = "Stable distribution among existing companies."
    return schemas.TruckerAnalysis(
        province_distribution=province_distribution,
        company_distribution=company_distribution,
        most_common_type=most_common_type,
        predictive_trend=predictive_trend
    )

@app.get("/analytics/business-impact", response_model=schemas.BusinessImpactAnalysis)
async def get_business_impact(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    total_employees_ever = db.query(models.Employee).count() + db.query(models.ArchivedEmployee).count()
    archived_employees_count = db.query(models.ArchivedEmployee).count()
    employee_churn_rate = (archived_employees_count / total_employees_ever) * 100 if total_employees_ever > 0 else 0.0
    total_truckers_ever = db.query(models.Trucker).count() + db.query(models.ArchivedTrucker).count()
    archived_truckers_count = db.query(models.ArchivedTrucker).count()
    trucker_churn_rate = (archived_truckers_count / total_truckers_ever) * 100 if total_truckers_ever > 0 else 0.0
    total_documents = db.query(models.Document).count() + db.query(models.ArchivedDocument).count()
    verified_documents = db.query(models.Document).filter(models.Document.is_verified == True).count()
    document_compliance_rate = (verified_documents / total_documents) * 100 if total_documents > 0 else 0.0
    return schemas.BusinessImpactAnalysis(
        employee_churn_rate=round(employee_churn_rate, 2),
        trucker_churn_rate=round(trucker_churn_rate, 2),
        document_compliance_rate=round(document_compliance_rate, 2),
        potential_revenue_impact="Improved compliance reduces risks and potential fines, leading to stable revenue.",
        operational_efficiency_impact="Automated document verification and personnel tracking streamline operations.",
        strategic_recommendations=[
            "Implement continuous compliance monitoring.",
            "Enhance training for new personnel to reduce churn.",
            "Explore partnerships with dominant trucking companies for better integration."
        ]
    )

# --- Data Export Endpoints ---
@app.get("/export/employees")
async def export_employees_to_csv(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    employees = db.query(models.Employee).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "First Name", "Last Name", "Email", "Phone Number", "Position", "Is Active", "Registration Date"])
    for emp in employees:
        writer.writerow([emp.id, emp.first_name, emp.last_name, emp.email, emp.phone_number, emp.position, emp.is_active, emp.registration_date])
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=employees.csv"})

@app.get("/export/truckers")
async def export_truckers_to_csv(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_admin)):
    truckers = db.query(models.Trucker).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "First Name", "Last Name", "Email", "Phone Number", "Driver License", "Province", "Truck ID", "Company", "Is Active", "Registration Date"])
    for trk in truckers:
        writer.writerow([trk.id, trk.first_name, trk.last_name, trk.email, trk.phone_number, trk.driver_license_number, trk.province_of_issue, trk.truck_id_number, trk.company_name, trk.is_active, trk.registration_date])
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=truckers.csv"})
