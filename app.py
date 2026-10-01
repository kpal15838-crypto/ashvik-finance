from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import traceback
from functools import wraps

# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "ASHVIK_FINANCE_SECRET_KEY_2026"
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "ashvik.db")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    conn = sqlite3.connect(
        DATABASE,
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA busy_timeout = 30000"
    )

    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    # -----------------------------------------------------
    # LOANS TABLE
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_name TEXT,
            loan_type TEXT,
            title TEXT,
            description TEXT,
            amount TEXT,
            interest TEXT,
            tenure TEXT,
            eligibility TEXT
        )
    """)

    # -----------------------------------------------------
    # APPLICATIONS TABLE
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT,
            city TEXT,
            address TEXT,
            employment TEXT,
            monthly_income TEXT,
            loan_amount TEXT,
            message TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(id)
        )
    """)

    # -----------------------------------------------------
    # CHECK LOANS COLUMNS
    # -----------------------------------------------------

    loan_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(loans)"
        ).fetchall()
    ]

    columns_to_add = {
        "loan_name": "TEXT",
        "loan_type": "TEXT",
        "title": "TEXT",
        "description": "TEXT",
        "amount": "TEXT",
        "interest": "TEXT",
        "tenure": "TEXT",
        "eligibility": "TEXT"
    }

    for column, data_type in columns_to_add.items():

        if column not in loan_columns:

            conn.execute(
                f"ALTER TABLE loans ADD COLUMN {column} {data_type}"
            )

    # -----------------------------------------------------
    # CHECK APPLICATION COLUMNS
    # -----------------------------------------------------

    application_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(applications)"
        ).fetchall()
    ]

    application_columns_to_add = {
        "loan_id": "INTEGER",
        "name": "TEXT",
        "mobile": "TEXT",
        "email": "TEXT",
        "city": "TEXT",
        "address": "TEXT",
        "employment": "TEXT",
        "monthly_income": "TEXT",
        "loan_amount": "TEXT",
        "message": "TEXT",
        "status": "TEXT DEFAULT 'Pending'",
        "created_at": "TIMESTAMP"
    }

    for column, data_type in application_columns_to_add.items():

        if column not in application_columns:

            conn.execute(
                f"ALTER TABLE applications ADD COLUMN {column} {data_type}"
            )

    # -----------------------------------------------------
    # OLD DATA COMPATIBILITY
    # -----------------------------------------------------

    conn.execute("""
        UPDATE loans
        SET title = loan_name
        WHERE
            (title IS NULL OR title = '')
            AND loan_name IS NOT NULL
    """)

    conn.execute("""
        UPDATE loans
        SET loan_name = title
        WHERE
            (loan_name IS NULL OR loan_name = '')
            AND title IS NOT NULL
    """)

    conn.execute("""
        UPDATE loans
        SET loan_type = title
        WHERE
            (loan_type IS NULL OR loan_type = '')
            AND title IS NOT NULL
    """)

    conn.commit()
    conn.close()

    print("======================================")
    print("ASHVIK DATABASE READY")
    print("DATABASE:", DATABASE)
    print("======================================")


# =========================================================
# ADMIN LOGIN DECORATOR
# =========================================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("admin_logged_in"):

            return redirect(
                url_for("admin_login")
            )

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# WELCOME / START PAGE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "welcome.html"
    )


# =========================================================
# USER HOME
# =========================================================

@app.route("/user")
def user_home():

    conn = get_db()

    loans = conn.execute("""
        SELECT *
        FROM loans
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        loans=loans
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return "ASHVIK OK - SERVER WORKING"


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        if (
            username == "admin"
            and password == "ashvik123"
        ):

            session["admin_logged_in"] = True
            session["admin_username"] = username

            flash(
                "Admin login successful!",
                "success"
            )

            return redirect(
                url_for("admin_panel")
            )

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template(
        "admin_login.html"
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@app.route("/admin")
@admin_required
def admin_panel():

    conn = get_db()

    loans = conn.execute("""
        SELECT *
        FROM loans
        ORDER BY id DESC
    """).fetchall()

    applications = conn.execute("""
        SELECT
            applications.*,
            COALESCE(
                loans.title,
                loans.loan_name,
                loans.loan_type
            ) AS loan_title
        FROM applications
        LEFT JOIN loans
            ON applications.loan_id = loans.id
        ORDER BY applications.id DESC
    """).fetchall()

    total_loans = conn.execute("""
        SELECT COUNT(*) AS total
        FROM loans
    """).fetchone()["total"]

    total_applications = conn.execute("""
        SELECT COUNT(*) AS total
        FROM applications
    """).fetchone()["total"]

    pending_applications = conn.execute("""
        SELECT COUNT(*) AS total
        FROM applications
        WHERE status = 'Pending'
    """).fetchone()["total"]

    approved_applications = conn.execute("""
        SELECT COUNT(*) AS total
        FROM applications
        WHERE status = 'Approved'
    """).fetchone()["total"]

    conn.close()

    return render_template(
        "admin.html",
        loans=loans,
        applications=applications,
        total_loans=total_loans,
        total_applications=total_applications,
        pending_applications=pending_applications,
        approved_applications=approved_applications
    )


# =========================================================
# ADD LOAN
# =========================================================

@app.route(
    "/admin/loan/add",
    methods=["POST"]
)
@admin_required
def add_loan():

    conn = None

    try:

        title = request.form.get(
            "title",
            ""
        ).strip()

        if not title:

            title = request.form.get(
                "loan_name",
                ""
            ).strip()

        if not title:

            title = request.form.get(
                "loan_title",
                ""
            ).strip()

        amount = request.form.get(
            "amount",
            ""
        ).strip()

        interest = request.form.get(
            "interest",
            ""
        ).strip()

        tenure = request.form.get(
            "tenure",
            ""
        ).strip()

        eligibility = request.form.get(
            "eligibility",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not title:

            flash(
                "Loan title is required.",
                "error"
            )

            return redirect(
                url_for("admin_panel")
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO loans
            (
                loan_name,
                loan_type,
                title,
                description,
                amount,
                interest,
                tenure,
                eligibility
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            title,
            title,
            description,
            amount,
            interest,
            tenure,
            eligibility
        ))

        conn.commit()

        flash(
            "Loan added successfully!",
            "success"
        )

    except Exception as e:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        traceback.print_exc()

        flash(
            "Loan add error: " + str(e),
            "error"
        )

    finally:

        if conn:

            try:
                conn.close()
            except Exception:
                pass

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# EDIT LOAN
# =========================================================

@app.route(
    "/admin/loan/edit/<int:loan_id>",
    methods=["GET", "POST"]
)
@admin_required
def edit_loan(loan_id):

    conn = get_db()

    loan = conn.execute("""
        SELECT *
        FROM loans
        WHERE id = ?
    """, (loan_id,)).fetchone()

    if not loan:

        conn.close()

        flash(
            "Loan not found.",
            "error"
        )

        return redirect(
            url_for("admin_panel")
        )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        amount = request.form.get(
            "amount",
            ""
        ).strip()

        interest = request.form.get(
            "interest",
            ""
        ).strip()

        tenure = request.form.get(
            "tenure",
            ""
        ).strip()

        eligibility = request.form.get(
            "eligibility",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not title:

            conn.close()

            flash(
                "Loan title is required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_loan",
                    loan_id=loan_id
                )
            )

        try:

            conn.execute("""
                UPDATE loans
                SET
                    loan_name = ?,
                    loan_type = ?,
                    title = ?,
                    description = ?,
                    amount = ?,
                    interest = ?,
                    tenure = ?,
                    eligibility = ?
                WHERE id = ?
            """, (
                title,
                title,
                title,
                description,
                amount,
                interest,
                tenure,
                eligibility,
                loan_id
            ))

            conn.commit()
            conn.close()

            flash(
                "Loan updated successfully!",
                "success"
            )

            return redirect(
                url_for("admin_panel")
            )

        except Exception as e:

            conn.rollback()
            conn.close()

            traceback.print_exc()

            flash(
                "Loan update error: " + str(e),
                "error"
            )

            return redirect(
                url_for(
                    "edit_loan",
                    loan_id=loan_id
                )
            )

    conn.close()

    return render_template(
        "edit_loan.html",
        loan=loan
    )


# =========================================================
# DELETE LOAN
# =========================================================

@app.route(
    "/admin/loan/delete/<int:loan_id>",
    methods=["POST"]
)
@admin_required
def delete_loan(loan_id):

    conn = get_db()

    try:

        conn.execute("""
            DELETE FROM applications
            WHERE loan_id = ?
        """, (loan_id,))

        conn.execute("""
            DELETE FROM loans
            WHERE id = ?
        """, (loan_id,))

        conn.commit()

        flash(
            "Loan deleted successfully!",
            "success"
        )

    except Exception as e:

        conn.rollback()

        traceback.print_exc()

        flash(
            "Loan delete error: " + str(e),
            "error"
        )

    finally:

        conn.close()

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# LOAN DETAILS
# =========================================================

@app.route(
    "/loan/<int:loan_id>"
)
def loan_details(loan_id):

    conn = get_db()

    loan = conn.execute("""
        SELECT *
        FROM loans
        WHERE id = ?
    """, (loan_id,)).fetchone()

    conn.close()

    if not loan:

        flash(
            "Loan not found.",
            "error"
        )

        return redirect(
            url_for("user_home")
        )

    return render_template(
        "loan_details.html",
        loan=loan
    )


# =========================================================
# APPLY FOR LOAN
# =========================================================

@app.route(
    "/apply",
    methods=["GET", "POST"]
)
def apply():

    loan_id = request.args.get(
        "loan_id"
    )

    if request.method == "POST":

        loan_id = request.form.get(
            "loan_id"
        )

        name = request.form.get(
            "name",
            ""
        ).strip()

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        city = request.form.get(
            "city",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        employment = request.form.get(
            "employment",
            ""
        ).strip()

        monthly_income = request.form.get(
            "monthly_income",
            ""
        ).strip()

        loan_amount = request.form.get(
            "loan_amount",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not name:

            flash(
                "Please enter your name.",
                "error"
            )

            return redirect(
                url_for(
                    "apply",
                    loan_id=loan_id
                )
            )

        if not mobile:

            flash(
                "Please enter your mobile number.",
                "error"
            )

            return redirect(
                url_for(
                    "apply",
                    loan_id=loan_id
                )
            )

        conn = None

        try:

            conn = get_db()

            conn.execute("""
                INSERT INTO applications
                (
                    loan_id,
                    name,
                    mobile,
                    email,
                    city,
                    address,
                    employment,
                    monthly_income,
                    loan_amount,
                    message,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                loan_id if loan_id else None,
                name,
                mobile,
                email,
                city,
                address,
                employment,
                monthly_income,
                loan_amount,
                message,
                "Pending"
            ))

            conn.commit()
            conn.close()

            return redirect(
                url_for("application_success")
            )

        except Exception as e:

            if conn:

                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass

            traceback.print_exc()

            flash(
                "Application error: " + str(e),
                "error"
            )

            return redirect(
                url_for(
                    "apply",
                    loan_id=loan_id
                )
            )

    loan = None

    if loan_id:

        conn = get_db()

        loan = conn.execute("""
            SELECT *
            FROM loans
            WHERE id = ?
        """, (loan_id,)).fetchone()

        conn.close()

    return render_template(
        "apply.html",
        loan=loan
    )


# =========================================================
# APPLICATION SUCCESS
# =========================================================

@app.route(
    "/application-success"
)
def application_success():

    return render_template(
        "application_success.html"
    )


# =========================================================
# APPLICATION STATUS
# =========================================================

@app.route(
    "/admin/application/status/<int:application_id>",
    methods=["POST"]
)
@admin_required
def update_application_status(application_id):

    status = request.form.get(
        "status",
        "Pending"
    ).strip()

    allowed_statuses = [
        "Pending",
        "Approved",
        "Rejected",
        "Contacted"
    ]

    if status not in allowed_statuses:

        status = "Pending"

    conn = get_db()

    try:

        conn.execute("""
            UPDATE applications
            SET status = ?
            WHERE id = ?
        """, (
            status,
            application_id
        ))

        conn.commit()

        flash(
            "Application status updated!",
            "success"
        )

    except Exception as e:

        conn.rollback()

        traceback.print_exc()

        flash(
            "Status update error: " + str(e),
            "error"
        )

    finally:

        conn.close()

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# DELETE APPLICATION
# =========================================================

@app.route(
    "/admin/application/delete/<int:application_id>",
    methods=["POST"]
)
@admin_required
def delete_application(application_id):

    conn = get_db()

    try:

        conn.execute("""
            DELETE FROM applications
            WHERE id = ?
        """, (application_id,))

        conn.commit()

        flash(
            "Application deleted successfully!",
            "success"
        )

    except Exception as e:

        conn.rollback()

        traceback.print_exc()

        flash(
            "Application delete error: " + str(e),
            "error"
        )

    finally:

        conn.close()

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# USER PANEL
# =========================================================

@app.route(
    "/user-panel"
)
def user_panel():

    conn = get_db()

    loans = conn.execute("""
        SELECT *
        FROM loans
        ORDER BY id DESC
    """).fetchall()

    applications = conn.execute("""
        SELECT
            applications.*,
            COALESCE(
                loans.title,
                loans.loan_name,
                loans.loan_type
            ) AS loan_title
        FROM applications
        LEFT JOIN loans
            ON applications.loan_id = loans.id
        ORDER BY applications.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "user_panel.html",
        loans=loans,
        applications=applications
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@app.errorhandler(Exception)
def handle_error(error):

    error_text = traceback.format_exc()

    print()
    print("=" * 70)
    print("ASHVIK INTERNAL SERVER ERROR")
    print("=" * 70)
    print(error_text)
    print("=" * 70)

    try:

        error_file = os.path.join(
            BASE_DIR,
            "ashvik_error.txt"
        )

        with open(
            error_file,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "ASHVIK INTERNAL SERVER ERROR\n\n"
            )

            file.write(
                error_text
            )

    except Exception:
        pass

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ASHVIK Error</title>

        <style>

            body {
                background: #0f172a;
                color: white;
                font-family: Arial, sans-serif;
                padding: 30px;
            }

            h1 {
                color: #ff6b6b;
            }

            pre {
                background: #020617;
                padding: 20px;
                border-radius: 12px;
                overflow-x: auto;
                white-space: pre-wrap;
                line-height: 1.5;
            }

        </style>

    </head>

    <body>

        <h1>
            ASHVIK Internal Server Error
        </h1>

        <p>
            Exact error:
        </p>

        <pre>
""" + error_text + """
        </pre>

    </body>
    </html>
    """, 500


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False,
        use_reloader=False
    )