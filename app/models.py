from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    email = Column(String, unique=True)
    full_name = Column(String)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    phone_number = Column(String)
    position = Column(String)
    is_active = Column(Boolean, default=True)
    registration_date = Column(Date, default=Date.today)
    documents = relationship("Document", back_populates="employee")

class Trucker(Base):
    __tablename__ = "truckers"
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    phone_number = Column(String)
    driver_license_number = Column(String, unique=True)
    province_of_issue = Column(String)
    truck_id_number = Column(String)
    company_name = Column(String)
    is_active = Column(Boolean, default=True)
    registration_date = Column(Date, default=Date.today)
    documents = relationship("Document", back_populates="trucker")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    document_type = Column(String)
    file_path = Column(String)
    upload_date = Column(Date, default=Date.today)
    is_verified = Column(Boolean, default=False)
    verification_date = Column(Date)
    verified_by = Column(String)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    trucker_id = Column(Integer, ForeignKey("truckers.id"))
    employee = relationship("Employee", back_populates="documents")
    trucker = relationship("Trucker", back_populates="documents")

class ArchivedEmployee(Base):
    __tablename__ = "archived_employees"
    id = Column(Integer, primary_key=True)
    original_id = Column(Integer)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone_number = Column(String)
    position = Column(String)
    is_active = Column(Boolean)
    registration_date = Column(Date)
    archive_date = Column(Date)
    archived_reason = Column(String)

class ArchivedTrucker(Base):
    __tablename__ = "archived_truckers"
    id = Column(Integer, primary_key=True)
    original_id = Column(Integer)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone_number = Column(String)
    driver_license_number = Column(String)
    province_of_issue = Column(String)
    truck_id_number = Column(String)
    company_name = Column(String)
    is_active = Column(Boolean)
    registration_date = Column(Date)
    archive_date = Column(Date)
    archived_reason = Column(String)

class ArchivedDocument(Base):
    __tablename__ = "archived_documents"
    id = Column(Integer, primary_key=True)
    original_id = Column(Integer)
    document_type = Column(String)
    file_path = Column(String)
    upload_date = Column(Date)
    is_verified = Column(Boolean)
    verification_date = Column(Date)
    verified_by = Column(String)
    employee_id = Column(Integer)
    trucker_id = Column(Integer)
    archive_date = Column(Date)
    archived_reason = Column(String)
