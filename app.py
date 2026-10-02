from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

import sqlite3
import os
import traceback
import uuid

from functools import wraps
from werkzeug.utils import secure_filename


# ============================================================
# ASHVIK FINANCE - FLASK APP
# ============================================================

app = Flask(__name__)

app.url_map.strict_slashes = False

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "ASHVIK_FINANCE_SECRET_KEY_2026"
)


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)


# ============================================================
# DATABASE
# ============================================================

DATABASE = os.path.join(
    BASE_DIR,
    "ashvik.db"
)


# ============================================================
# UPLOAD FOLDER
# ============================================================

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# ============================================================
# ALLOWED IMAGES
# ============================================================

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif"
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    conn = sqlite3.connect(
        DATABASE,
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA busy_timeout = 30000"
    )

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# ============================================================
# IMAGE VALIDATION
# ============================================================

def allowed_image(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = get_db()

    try:

        # ====================================================
        # LOANS
        # ====================================================

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


        # ====================================================
        # APPLICATIONS
        # ====================================================

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

                FOREIGN KEY (loan_id)
                    REFERENCES loans(id)

            )
        """)


        # ====================================================
        # OWNER PROFILE
        # ====================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS owner_profile (

                id INTEGER PRIMARY KEY,

                owner_name TEXT,

                owner_photo TEXT,

                owner_mobile TEXT,

                owner_email TEXT,

                company_name TEXT,

                office_address TEXT,

                about TEXT

            )
        """)


        # ====================================================
        # OWNER MIGRATION
        # ====================================================

        owner_columns = [
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(owner_profile)"
            ).fetchall()
        ]


        owner_columns_to_add = {

            "owner_name": "TEXT",
            "owner_photo": "TEXT",
            "owner_mobile": "TEXT",
            "owner_email": "TEXT",
            "company_name": "TEXT",
            "office_address": "TEXT",
            "about": "TEXT"

        }


        for column, data_type in owner_columns_to_add.items():

            if column not in owner_columns:

                conn.execute(
                    f"""
                    ALTER TABLE owner_profile
                    ADD COLUMN {column} {data_type}
                    """
                )


        # ====================================================
        # DEFAULT OWNER
        # ====================================================

        owner_exists = conn.execute("""
            SELECT id
            FROM owner_profile
            WHERE id = 1
        """).fetchone()


        if not owner_exists:

            conn.execute("""
                INSERT INTO owner_profile
                (
                    id,
                    owner_name,
                    owner_photo,
                    owner_mobile,
                    owner_email,
                    company_name,
                    office_address,
                    about
                )
                VALUES
                (
                    1,
                    '',
                    '',
                    '',
                    '',
                    'ASHVIK FINANCE',
                    '',
                    ''
                )
            """)


        # ====================================================
        # LOAN MIGRATION
        # ====================================================

        loan_columns = [
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(loans)"
            ).fetchall()
        ]


        loan_columns_to_add = {

            "loan_name": "TEXT",
            "loan_type": "TEXT",
            "title": "TEXT",
            "description": "TEXT",
            "amount": "TEXT",
            "interest": "TEXT",
            "tenure": "TEXT",
            "eligibility": "TEXT"

        }


        for column, data_type in loan_columns_to_add.items():

            if column not in loan_columns:

                conn.execute(
                    f"""
                    ALTER TABLE loans
                    ADD COLUMN {column} {data_type}
                    """
                )


        # ====================================================
        # APPLICATION MIGRATION
        # ====================================================

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
            "status": "TEXT",
            "created_at": "TIMESTAMP"

        }


        for column, data_type in application_columns_to_add.items():

            if column not in application_columns:

                conn.execute(
                    f"""
                    ALTER TABLE applications
                    ADD COLUMN {column} {data_type}
                    """
                )


        # ====================================================
        # OLD NULL DATES
        # ====================================================

        try:

            conn.execute("""
                UPDATE applications

                SET created_at = CURRENT_TIMESTAMP

                WHERE created_at IS NULL
            """)

        except Exception:

            pass


        # ====================================================
        # OLD LOAN DATA SYNC
        # ====================================================

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


        # ====================================================
        # APPLICATION STATUS FIX
        # ====================================================

        conn.execute("""
            UPDATE applications

            SET status = 'Pending'

            WHERE
                status IS NULL
                OR status = ''
        """)


        conn.commit()


        print()
        print("=" * 60)
        print("ASHVIK FINANCE DATABASE READY")
        print("=" * 60)

        print("DATABASE:")
        print(DATABASE)

        print()

        print("OWNER PROFILE: READY")

        print()

        print("UPLOAD FOLDER:")
        print(UPLOAD_FOLDER)

        print("=" * 60)
        print()


    except Exception:

        conn.rollback()

        print()
        print("=" * 60)
        print("ASHVIK DATABASE ERROR")
        print("=" * 60)

        traceback.print_exc()

        raise


    finally:

        conn.close()


# ============================================================
# GET OWNER
# ============================================================

def get_owner():

    conn = get_db()

    owner = conn.execute("""
        SELECT *
        FROM owner_profile
        WHERE id = 1
    """).fetchone()

    conn.close()

    return owner


# ============================================================
# OWNER AVAILABLE IN ALL TEMPLATES
# ============================================================

@app.context_processor
def inject_owner():

    try:

        owner = get_owner()

        return {
            "owner": owner
        }

    except Exception:

        return {
            "owner": None
        }


# ============================================================
# ADMIN LOGIN REQUIRED
# ============================================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get(
            "admin_logged_in"
        ):

            return redirect(
                url_for("admin_login")
            )

        return function(
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "welcome.html"
    )


# ============================================================
# USER OLD URL
# IMPORTANT:
# /user ab User Panel par jayega
# ============================================================

@app.route("/user")
def user_home():

    return redirect(
        url_for("user_panel")
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return "ASHVIK OK - SERVER WORKING"


# ============================================================
# ADMIN LOGIN
# ============================================================

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
            and
            password == "ashvik123"
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


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@admin_required
def admin_panel():

    conn = get_db()


    # ========================================================
    # LOANS
    # ========================================================

    loans = conn.execute("""
        SELECT *
        FROM loans
        ORDER BY id DESC
    """).fetchall()


    # ========================================================
    # APPLICATIONS
    # ========================================================

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


    # ========================================================
    # STATISTICS
    # ========================================================

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


# ============================================================
# SAVE OWNER PROFILE
# ============================================================

def save_owner_profile():

    conn = get_db()


    owner = conn.execute("""
        SELECT *
        FROM owner_profile
        WHERE id = 1
    """).fetchone()


    owner_name = request.form.get(
        "owner_name",
        ""
    ).strip()


    owner_mobile = request.form.get(
        "owner_mobile",
        ""
    ).strip()


    owner_email = request.form.get(
        "owner_email",
        ""
    ).strip()


    company_name = request.form.get(
        "company_name",
        ""
    ).strip()


    office_address = request.form.get(
        "office_address",
        ""
    ).strip()


    about = request.form.get(
        "about",
        ""
    ).strip()


    old_photo = ""

    if owner:

        old_photo = (
            owner["owner_photo"]
            or ""
        )


    new_photo_path = old_photo

    new_saved_file = None


    # ========================================================
    # OWNER PHOTO
    # ========================================================

    uploaded_file = request.files.get(
        "owner_photo"
    )


    if (
        uploaded_file
        and
        uploaded_file.filename
    ):

        original_filename = secure_filename(
            uploaded_file.filename
        )


        if not allowed_image(
            original_filename
        ):

            conn.close()

            flash(
                "Only JPG, JPEG, PNG, WEBP or GIF images are allowed.",
                "error"
            )

            return False


        extension = original_filename.rsplit(
            ".",
            1
        )[1].lower()


        unique_filename = (
            "owner_"
            +
            uuid.uuid4().hex
            +
            "."
            +
            extension
        )


        full_path = os.path.join(
            UPLOAD_FOLDER,
            unique_filename
        )


        try:

            uploaded_file.save(
                full_path
            )

            new_saved_file = full_path

            new_photo_path = (
                "uploads/"
                +
                unique_filename
            )


        except Exception as e:

            conn.close()

            traceback.print_exc()

            flash(
                "Owner photo upload error: "
                +
                str(e),
                "error"
            )

            return False


    # ========================================================
    # MAKE SURE OWNER ROW EXISTS
    # ========================================================

    try:

        owner_check = conn.execute("""
            SELECT id
            FROM owner_profile
            WHERE id = 1
        """).fetchone()


        if not owner_check:

            conn.execute("""
                INSERT INTO owner_profile
                (
                    id,
                    owner_name,
                    owner_photo,
                    owner_mobile,
                    owner_email,
                    company_name,
                    office_address,
                    about
                )
                VALUES
                (
                    1,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
            """, (

                owner_name,
                new_photo_path,
                owner_mobile,
                owner_email,
                company_name,
                office_address,
                about

            ))

        else:

            conn.execute("""
                UPDATE owner_profile

                SET

                    owner_name = ?,

                    owner_photo = ?,

                    owner_mobile = ?,

                    owner_email = ?,

                    company_name = ?,

                    office_address = ?,

                    about = ?

                WHERE id = 1

            """, (

                owner_name,

                new_photo_path,

                owner_mobile,

                owner_email,

                company_name,

                office_address,

                about

            ))


        conn.commit()

        conn.close()


        # ====================================================
        # DELETE OLD PHOTO
        # ====================================================

        if (
            new_photo_path != old_photo
            and
            old_photo
        ):

            old_filename = old_photo.replace(
                "uploads/",
                ""
            )


            old_file_path = os.path.join(
                UPLOAD_FOLDER,
                old_filename
            )


            try:

                if os.path.exists(
                    old_file_path
                ):

                    os.remove(
                        old_file_path
                    )

            except Exception:

                pass


        flash(
            "Owner profile updated successfully!",
            "success"
        )

        return True


    except Exception as e:

        try:

            conn.rollback()

        except Exception:

            pass


        conn.close()


        if new_saved_file:

            try:

                if os.path.exists(
                    new_saved_file
                ):

                    os.remove(
                        new_saved_file
                    )

            except Exception:

                pass


        traceback.print_exc()


        flash(
            "Owner profile update error: "
            +
            str(e),
            "error"
        )

        return False


# ============================================================
# OWNER PROFILE
# ============================================================

@app.route(
    "/admin/owner",
    methods=["GET", "POST"],
    strict_slashes=False
)
@admin_required
def owner_settings():

    if request.method == "POST":

        save_owner_profile()

        return redirect(
            url_for("owner_settings")
        )


    owner = get_owner()


    return render_template(
        "admin_owner.html",
        owner=owner
    )


# ============================================================
# OWNER BACKUP URL
# ============================================================

@app.route(
    "/admin-owner",
    methods=["GET", "POST"],
    strict_slashes=False
)
@admin_required
def admin_owner_backup():

    if request.method == "POST":

        save_owner_profile()

        return redirect(
            url_for("admin_owner_backup")
        )


    owner = get_owner()


    return render_template(
        "admin_owner.html",
        owner=owner
    )


# ============================================================
# OWNER ALTERNATE URL
# ============================================================

@app.route(
    "/admin/profile",
    methods=["GET", "POST"],
    strict_slashes=False
)
@admin_required
def admin_profile():

    if request.method == "POST":

        save_owner_profile()

        return redirect(
            url_for("admin_profile")
        )


    owner = get_owner()


    return render_template(
        "admin_owner.html",
        owner=owner
    )


# ============================================================
# ADD LOAN
# ============================================================

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
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
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
            "Loan add error: "
            +
            str(e),
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


# ============================================================
# EDIT LOAN
# ============================================================

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
    """, (
        loan_id,
    )).fetchone()


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
                "Loan update error: "
                +
                str(e),
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


# ============================================================
# DELETE LOAN
# ============================================================

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
        """, (
            loan_id,
        ))


        conn.execute("""
            DELETE FROM loans
            WHERE id = ?
        """, (
            loan_id,
        ))


        conn.commit()


        flash(
            "Loan deleted successfully!",
            "success"
        )


    except Exception as e:

        conn.rollback()

        traceback.print_exc()


        flash(
            "Loan delete error: "
            +
            str(e),
            "error"
        )


    finally:

        conn.close()


    return redirect(
        url_for("admin_panel")
    )


# ============================================================
# LOAN DETAILS
# ============================================================

@app.route(
    "/loan/<int:loan_id>"
)
def loan_details(loan_id):

    conn = get_db()


    loan = conn.execute("""
        SELECT *
        FROM loans
        WHERE id = ?
    """, (
        loan_id,
    )).fetchone()


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


# ============================================================
# APPLY
# ============================================================

@app.route(
    "/apply",
    methods=["GET", "POST"]
)
def apply():

    loan_id = request.args.get(
        "loan_id"
    )


    # ========================================================
    # POST
    # ========================================================

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
                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
            """, (

                loan_id
                if loan_id
                else None,

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
                url_for(
                    "application_success"
                )
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
                "Application error: "
                +
                str(e),
                "error"
            )


            return redirect(
                url_for(
                    "apply",
                    loan_id=loan_id
                )
            )


    # ========================================================
    # GET LOAN
    # ========================================================

    loan = None


    if loan_id:

        conn = get_db()


        loan = conn.execute("""
            SELECT *
            FROM loans
            WHERE id = ?
        """, (
            loan_id,
        )).fetchone()


        conn.close()


    return render_template(
        "apply.html",
        loan=loan
    )


# ============================================================
# APPLICATION SUCCESS
# ============================================================

@app.route(
    "/application-success"
)
def application_success():

    return render_template(
        "application_success.html"
    )


# ============================================================
# UPDATE APPLICATION STATUS
# ============================================================

@app.route(
    "/admin/application/status/<int:application_id>",
    methods=["POST"]
)
@admin_required
def update_application_status(
    application_id
):

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
            "Status update error: "
            +
            str(e),
            "error"
        )


    finally:

        conn.close()


    return redirect(
        url_for("admin_panel")
    )


# ============================================================
# DELETE APPLICATION
# ============================================================

@app.route(
    "/admin/application/delete/<int:application_id>",
    methods=["POST"]
)
@admin_required
def delete_application(
    application_id
):

    conn = get_db()


    try:

        conn.execute("""
            DELETE FROM applications
            WHERE id = ?
        """, (
            application_id,
        ))


        conn.commit()


        flash(
            "Application deleted successfully!",
            "success"
        )


    except Exception as e:

        conn.rollback()

        traceback.print_exc()


        flash(
            "Application delete error: "
            +
            str(e),
            "error"
        )


    finally:

        conn.close()


    return redirect(
        url_for("admin_panel")
    )


# ============================================================
# USER PANEL
# IMPORTANT FIX
# ============================================================

@app.route(
    "/user-panel"
)
def user_panel():

    conn = get_db()


    # ========================================================
    # LOANS
    # ========================================================

    loans = conn.execute("""
        SELECT *
        FROM loans
        ORDER BY id DESC
    """).fetchall()


    # ========================================================
    # APPLICATIONS
    # ========================================================

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


    # ========================================================
    # OWNER
    # ========================================================

    owner = get_owner()


    # ========================================================
    # IMPORTANT:
    # owner EXPLICITLY user_panel.html ko diya ja raha hai
    # ========================================================

    return render_template(
        "user_panel.html",

        loans=loans,

        applications=applications,

        owner=owner
    )


# ============================================================
# FILE TOO LARGE
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>ASHVIK - File Too Large</title>

        <style>

            body {
                background:#0f172a;
                color:white;
                font-family:Arial,sans-serif;
                padding:40px;
                text-align:center;
            }

            .box {
                max-width:600px;
                margin:50px auto;
                background:#1e293b;
                padding:30px;
                border-radius:18px;
            }

            h1 {
                color:#f87171;
            }

            a {
                display:inline-block;
                margin-top:20px;
                background:#2563eb;
                color:white;
                text-decoration:none;
                padding:12px 20px;
                border-radius:8px;
            }

        </style>

    </head>

    <body>

        <div class="box">

            <h1>
                File Too Large
            </h1>

            <p>
                Owner photo maximum size is 5 MB.
            </p>

            <a href="/admin/owner">
                Back to Owner Profile
            </a>

        </div>

    </body>

    </html>
    """, 413


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    print()
    print("=" * 70)
    print("ASHVIK 404 - PAGE NOT FOUND")
    print("PATH:", request.path)
    print("=" * 70)


    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>ASHVIK - Page Not Found</title>

        <style>

            body {

                background:#0f172a;

                color:white;

                font-family:Arial,sans-serif;

                padding:30px;

                text-align:center;

            }

            .box {

                max-width:650px;

                margin:80px auto;

                background:#1e293b;

                padding:40px;

                border-radius:20px;

            }

            h1 {

                color:#f87171;

                font-size:45px;

            }

            a {

                display:inline-block;

                margin:10px;

                background:#2563eb;

                color:white;

                text-decoration:none;

                padding:12px 22px;

                border-radius:8px;

            }

        </style>

    </head>

    <body>

        <div class="box">

            <h1>404</h1>

            <h2>Page Not Found</h2>

            <p>
                The requested ASHVIK page does not exist.
            </p>

            <a href="/">
                Home
            </a>

            <a href="/user-panel">
                User Panel
            </a>

            <a href="/admin">
                Admin Dashboard
            </a>

        </div>

    </body>

    </html>
    """, 404


# ============================================================
# GLOBAL ERROR
# ============================================================

@app.errorhandler(Exception)
def handle_error(error):

    if getattr(error, "code", None) == 404:

        return page_not_found(error)


    error_text = traceback.format_exc()


    print()
    print("=" * 70)
    print("ASHVIK INTERNAL SERVER ERROR")
    print("=" * 70)

    print(error_text)

    print("=" * 70)


    # ========================================================
    # SAVE ERROR
    # ========================================================

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

                background:#0f172a;

                color:white;

                font-family:Arial,sans-serif;

                padding:30px;

            }

            .box {

                max-width:1100px;

                margin:auto;

            }

            h1 {

                color:#ff6b6b;

            }

            pre {

                background:#020617;

                padding:20px;

                border-radius:12px;

                overflow-x:auto;

                white-space:pre-wrap;

                line-height:1.5;

            }

            a {

                display:inline-block;

                margin-top:20px;

                background:#2563eb;

                color:white;

                text-decoration:none;

                padding:12px 20px;

                border-radius:8px;

            }

        </style>

    </head>

    <body>

        <div class="box">

            <h1>
                ASHVIK Internal Server Error
            </h1>

            <p>
                Exact error:
            </p>

            <pre>
""" + error_text + """
            </pre>

            <a href="/user-panel">
                Back to User Panel
            </a>

        </div>

    </body>

    </html>
    """, 500


# ============================================================
# START
# ============================================================

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