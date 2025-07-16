# eArbor IoT Data Platform

This is a backend system for managing IoT data, personnel, and analytics.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Set up a PostgreSQL database or SQLite.
3. Run the server: `uvicorn app.main:app --reload`
4. Access the API documentation at: `http://localhost:8000/docs`


Here is a **detailed description list of all the calculations** performed in the provided FastAPI code:

---

### 1. **JWT Token Expiration Time Calculation**
- **Where:** `create_access_token`
- **What:** Computes the expiration time of a JWT token.
- **How:** 
  - Adds a `timedelta` to the current UTC time if provided.
  - Otherwise, defaults to 30 minutes from the current time.
- **Used for:** Securing user sessions with short-lived tokens.

---

### 2. **Employee Monthly Registration Growth**
- **Where:** `get_employee_growth`
- **What:** Groups employee registrations by month and counts them.
- **How:** Uses SQLAlchemy's `func.strftime('%Y-%m', registration_date)` to group by year-month.
- **Used for:** Visualizing monthly employee growth trends.

---

### 3. **Average Monthly Employee Growth**
- **Where:** `get_employee_growth`
- **What:** Calculates the average number of new employees per month.
- **How:** Sums all monthly counts and divides by the number of months.
- **Used for:** Understanding long-term hiring trends.

---

### 4. **Employee Growth Projection (Linear Regression)**
- **Where:** `get_employee_growth`
- **What:** Predicts next month's employee growth using a simple linear regression.
- **How:** 
  - Uses `scikit-learn`'s `LinearRegression`.
  - Trains on month index (0, 1, 2...) and counts.
  - Predicts the next month's count.
- **Used for:** Forecasting hiring needs.

---

### 5. **Trucker Distribution by Province**
- **Where:** `get_trucker_distribution`
- **What:** Counts how many truckers are registered per province.
- **How:** Groups truckers by `province_of_issue` and counts.
- **Used for:** Geographic analytics of trucker presence.

---

### 6. **Trucker Distribution by Company (or Independent)**
- **Where:** `get_trucker_distribution`
- **What:** Counts how many truckers belong to each company, or are independent.
- **How:** Uses `func.coalesce(company_name, 'Independent')` to handle nulls.
- **Used for:** Understanding the business structure of the trucker base.

---

### 7. **Trucker Distribution Percentage Calculation**
- **Where:** `get_trucker_distribution`
- **What:** Calculates the percentage of truckers per company relative to the total.
- **How:** `(count / total_truckers) * 100`
- **Used for:** Visualizing the market share of each company.

---

### 8. **Most Common Trucker Type**
- **Where:** `get_trucker_distribution`
- **What:** Determines the most frequent company or independent status.
- **How:** Compares counts of each group.
- **Used for:** Identifying dominant trends in the trucking segment.

---

### 9. **Predictive Trend for Truckers**
- **Where:** `get_trucker_distribution`
- **What:** Simple logic-based trend prediction.
- **How:** 
  - If independent truckers > 40% → increasing trend towards independence.
  - If one company dominates (>60%) → dominance observed.
- **Used for:** Informing strategic decisions.

---

### 10. **Employee Churn Rate**
- **Where:** `get_business_impact`
- **What:** Calculates the percentage of employees who have been archived.
- **How:**  
  ```
  (archived_employees_count / total_employees_ever) * 100
  ```
- **Used for:** Measuring employee retention and attrition.

---

### 11. **Trucker Churn Rate**
- **Where:** `get_business_impact`
- **What:** Calculates the percentage of truckers who have been archived.
- **How:**  
  ```
  (archived_truckers_count / total_truckers_ever) * 100
  ```
- **Used for:** Measuring turnover in the trucking workforce.

---

### 12. **Document Compliance Rate**
- **Where:** `get_business_impact`
- **What:** Calculates the percentage of documents that are verified.
- **How:**  
  ```
  (verified_documents / total_documents) * 100
  ```
- **Used for:** Measuring regulatory compliance and documentation accuracy.

---

### 13. **Unverified Documents Count**
- **Where:** `get_compliance_data`
- **What:** Calculates how many documents are still unverified.
- **How:**  
  ```
  total_documents - verified_documents
  ```
- **Used for:** Monitoring document verification progress.

---

### 14. **Total and Active Counts**
- **Where:** `get_compliance_data`, `get_business_impact`
- **What:** Counts total and active employees and truckers.
- **How:** Uses SQLAlchemy `.count()` on filtered and unfiltered queries.
- **Used for:** Real-time headcount and status tracking.

---

### 15. **Verification Date Update Logic**
- **Where:** `update_document`
- **What:** Automatically sets or clears the verification date and verifier.
- **How:** 
  - If `is_verified` is `True` and `verification_date` is `None`, set to today.
  - If `is_verified` becomes `False`, clear `verification_date` and `verified_by`.
- **Used for:** Ensuring document verification timestamps are accurate.

---

### Summary Table

| Calculation | Description | Purpose |
|------------|-------------|---------|
| JWT Token Expiration | Sets token expiration time | Secure session management |
| Employee Monthly Growth | Groups by month and counts | Hiring trend analysis |
| Average Monthly Growth | Mean of monthly counts | Long-term trend analysis |
| Linear Regression Forecast | Predicts next month’s growth | Planning and forecasting |
| Trucker Province Distribution | Counts by province | Geographic analytics |
| Company Distribution | Counts by company or independent | Market structure |
| Percentage Distribution | % of truckers per company | Share of market |
| Most Common Type | Determines dominant group | Identifying trends |
| Predictive Trend | Logic-based trend prediction | Strategic planning |
| Employee Churn Rate | % of archived employees | Retention analysis |
| Trucker Churn Rate | % of archived truckers | Turnover analysis |
| Document Compliance Rate | % of verified documents | Compliance monitoring |
| Unverified Documents | Total - Verified | Verification backlog |
| Active Counts | Count of active employees/truckers | Headcount tracking |
| Verification Date Logic | Auto-update on status change | Audit and timestamping |

---

Let me know if you want these calculations exported into a **report**, **Excel**, or **CSV format** for documentation or stakeholder presentation!
