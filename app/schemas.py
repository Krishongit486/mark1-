from pydantic import BaseModel
from typing import Optional, List
from datetime import date

# --- Authentication Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    is_admin: bool = False

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# --- Employee Schemas ---
class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    position: str

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    position: Optional[str] = None

class DocumentOut(BaseModel):
    id: int
    document_type: str
    file_path: str
    upload_date: date
    is_verified: bool

    class Config:
        from_attributes = True

class EmployeeOutWithDocuments(EmployeeBase):
    id: int
    is_active: bool
    registration_date: date
    documents: List[DocumentOut] = []

    class Config:
        from_attributes = True

class EmployeeOut(EmployeeBase):
    id: int
    is_active: bool
    registration_date: date

    class Config:
        from_attributes = True

# --- Trucker Schemas ---
class TruckerBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    driver_license_number: str
    province_of_issue: str
    truck_id_number: Optional[str] = None
    company_name: Optional[str] = None

class TruckerCreate(TruckerBase):
    pass

class TruckerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    driver_license_number: Optional[str] = None
    province_of_issue: Optional[str] = None
    truck_id_number: Optional[str] = None
    company_name: Optional[str] = None

class TruckerOut(TruckerBase):
    id: int
    is_active: bool
    registration_date: date

    class Config:
        from_attributes = True

class TruckerOutWithDocuments(TruckerBase):
    id: int
    is_active: bool
    registration_date: date
    documents: List[DocumentOut] = []

    class Config:
        from_attributes = True

# --- Document Schemas ---
class DocumentBase(BaseModel):
    document_type: str
    file_path: str
    employee_id: Optional[int] = None
    trucker_id: Optional[int] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    is_verified: Optional[bool] = None

class DocumentOut(DocumentBase):
    id: int
    upload_date: date
    is_verified: bool
    verification_date: Optional[date] = None
    verified_by: Optional[str] = None

    class Config:
        from_attributes = True

# --- Analytics Schemas ---
class RegistrationGrowth(BaseModel):
    date: str
    count: int

class EmployeeGrowthAnalysis(BaseModel):
    monthly_growth: List[RegistrationGrowth]
    total_employees: int
    average_monthly_growth: float
    projected_next_month: Optional[int] = None

class TruckerTypeDistribution(BaseModel):
    company_name: str
    count: int
    percentage: float

class TruckerAnalysis(BaseModel):
    province_distribution: dict
    company_distribution: List[TruckerTypeDistribution]
    most_common_type: str
    predictive_trend: str

class ComplianceData(BaseModel):
    total_employees: int
    active_employees: int
    total_truckers: int
    active_truckers: int
    documents_uploaded: int
    documents_verified: int
    unverified_documents: int

class BusinessImpactAnalysis(BaseModel):
    employee_churn_rate: float
    trucker_churn_rate: float
    document_compliance_rate: float
    potential_revenue_impact: str
    operational_efficiency_impact: str
    strategic_recommendations: List[str]

class LiveSearchResult(BaseModel):
    type: str
    id: int
    name: str
    identifier: str
    is_active: bool
    details: dict
