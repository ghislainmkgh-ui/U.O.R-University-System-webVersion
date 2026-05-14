"""Unmanaged Django models for the existing U.O.R database.

These models document the current schema and make the web backend aware of the
tables without letting Django manage or recreate them.
"""
from django.db import models


class UnmanagedModel(models.Model):
    class Meta:
        abstract = True
        managed = False


class Faculty(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "faculty"


class Department(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    faculty = models.ForeignKey(Faculty, models.DO_NOTHING, db_column="faculty_id")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "department"


class Promotion(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    year = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    department = models.ForeignKey(Department, models.DO_NOTHING, db_column="department_id")
    fee_usd = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    threshold_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "promotion"


class AcademicYear(UnmanagedModel):
    academic_year_id = models.AutoField(primary_key=True)
    year_name = models.CharField(max_length=50)
    threshold_amount = models.DecimalField(max_digits=15, decimal_places=2)
    final_fee = models.DecimalField(max_digits=15, decimal_places=2)
    partial_valid_days = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "academic_year"


class ExamPeriod(UnmanagedModel):
    exam_period_id = models.AutoField(primary_key=True)
    academic_year = models.ForeignKey(AcademicYear, models.DO_NOTHING, db_column="academic_year_id")
    period_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "exam_period"


class Student(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    student_number = models.CharField(max_length=50)
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    passport_photo_path = models.CharField(max_length=512, blank=True, null=True)
    passport_photo_blob = models.BinaryField(blank=True, null=True)
    promotion = models.ForeignKey(Promotion, models.DO_NOTHING, db_column="promotion_id")
    academic_year = models.ForeignKey(
        AcademicYear,
        models.DO_NOTHING,
        db_column="academic_year_id",
        blank=True,
        null=True,
    )
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    face_encoding = models.BinaryField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "student"


class FaceTrainingPhoto(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, models.DO_NOTHING, db_column="student_id")
    photo_path = models.CharField(max_length=512, blank=True, null=True)
    photo_blob = models.BinaryField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "face_training_photos"


class FinanceProfile(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    student = models.OneToOneField(Student, models.DO_NOTHING, db_column="student_id")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    threshold_required = models.DecimalField(max_digits=10, decimal_places=2)
    last_payment_date = models.DateTimeField(blank=True, null=True)
    is_eligible = models.BooleanField(default=False)
    academic_year = models.ForeignKey(
        AcademicYear,
        models.DO_NOTHING,
        db_column="academic_year_id",
        blank=True,
        null=True,
    )
    access_code_issued_at = models.DateTimeField(blank=True, null=True)
    access_code_expires_at = models.DateTimeField(blank=True, null=True)
    access_code_type = models.CharField(max_length=20, blank=True, null=True)
    final_fee = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_profile"


class PaymentHistory(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, models.DO_NOTHING, db_column="student_id")
    amount_paid_fc = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid_usd = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_reference = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "payment_history"


class AccessCodeHistory(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, models.DO_NOTHING, db_column="student_id")
    access_code = models.CharField(max_length=20)
    access_type = models.CharField(max_length=20)
    expires_at = models.DateTimeField(blank=True, null=True)
    issued_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "access_code_history"


class AccessLog(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, models.DO_NOTHING, db_column="student_id")
    access_point = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=30)
    password_validated = models.BooleanField(default=False)
    face_validated = models.BooleanField(default=False)
    finance_validated = models.BooleanField(default=False)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "access_log"


class Administrator(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=255)
    email = models.CharField(max_length=255, blank=True, null=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_super_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "administrator"


class UserAccessRequest(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    password_hash = models.CharField(max_length=255)
    status = models.CharField(max_length=20)
    reviewed_by = models.CharField(max_length=255, blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    decision_note = models.TextField(blank=True, null=True)
    requested_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "user_access_request"


class AcademicRecord(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, models.DO_NOTHING, db_column="student_id")
    promotion = models.ForeignKey(Promotion, models.DO_NOTHING, db_column="promotion_id")
    academic_year = models.ForeignKey(
        AcademicYear,
        models.DO_NOTHING,
        db_column="academic_year_id",
        blank=True,
        null=True,
    )
    course_name = models.CharField(max_length=255)
    course_code = models.CharField(max_length=50, blank=True, null=True)
    credits = models.IntegerField(default=0)
    grade = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    grade_letter = models.CharField(max_length=5, blank=True, null=True)
    semester = models.CharField(max_length=20, blank=True, null=True)
    exam_date = models.DateField(blank=True, null=True)
    professor_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    is_transferred = models.BooleanField(default=False)
    source_university = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "academic_record"


class StudentDocument(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, models.DO_NOTHING, db_column="student_id")
    document_type = models.CharField(max_length=30)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    file_path = models.CharField(max_length=1024, blank=True, null=True)
    file_blob = models.BinaryField(blank=True, null=True)
    file_size_mb = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    issue_date = models.DateField(blank=True, null=True)
    return_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=30, blank=True, null=True)
    library_code = models.CharField(max_length=100, blank=True, null=True)
    is_transferred = models.BooleanField(default=False)
    source_university = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "student_document"


class TransferRequest(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    request_code = models.CharField(max_length=100)
    transfer_type = models.CharField(max_length=20)
    student = models.ForeignKey(Student, models.DO_NOTHING, db_column="student_id", blank=True, null=True)
    external_student_number = models.CharField(max_length=100, blank=True, null=True)
    external_firstname = models.CharField(max_length=255, blank=True, null=True)
    external_lastname = models.CharField(max_length=255, blank=True, null=True)
    external_email = models.CharField(max_length=255, blank=True, null=True)
    external_phone = models.CharField(max_length=20, blank=True, null=True)
    source_university = models.CharField(max_length=255)
    source_university_code = models.CharField(max_length=50, blank=True, null=True)
    destination_university = models.CharField(max_length=255, blank=True, null=True)
    destination_university_code = models.CharField(max_length=50, blank=True, null=True)
    target_promotion = models.ForeignKey(
        Promotion,
        models.DO_NOTHING,
        db_column="target_promotion_id",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=30)
    requested_date = models.DateTimeField(blank=True, null=True)
    reviewed_date = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.CharField(max_length=255, blank=True, null=True)
    received_data_json = models.TextField(blank=True, null=True)
    approval_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "transfer_request"


class TransferHistory(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    transfer_code = models.CharField(max_length=100)
    student = models.ForeignKey(Student, models.DO_NOTHING, db_column="student_id")
    transfer_type = models.CharField(max_length=20)
    source_university = models.CharField(max_length=255, blank=True, null=True)
    source_university_code = models.CharField(max_length=50, blank=True, null=True)
    destination_university = models.CharField(max_length=255, blank=True, null=True)
    destination_university_code = models.CharField(max_length=50, blank=True, null=True)
    transfer_date = models.DateTimeField()
    status = models.CharField(max_length=30)
    delivery_status = models.CharField(max_length=30, blank=True, null=True)
    delivery_message = models.TextField(blank=True, null=True)
    records_count = models.IntegerField(default=0)
    documents_count = models.IntegerField(default=0)
    total_credits = models.IntegerField(default=0)
    initiated_by = models.CharField(max_length=255, blank=True, null=True)
    validated_by = models.CharField(max_length=255, blank=True, null=True)
    validation_date = models.DateTimeField(blank=True, null=True)
    api_endpoint = models.CharField(max_length=512, blank=True, null=True)
    transfer_data_json = models.TextField(blank=True, null=True)
    response_json = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "transfer_history"


class PartnerUniversity(UnmanagedModel):
    id = models.AutoField(primary_key=True)
    university_name = models.CharField(max_length=255)
    university_code = models.CharField(max_length=50)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True, null=True)
    api_endpoint = models.CharField(max_length=512, blank=True, null=True)
    api_url = models.CharField(max_length=512, blank=True, null=True)
    api_key_encrypted = models.CharField(max_length=512, blank=True, null=True)
    authentication_type = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    trust_level = models.CharField(max_length=30, blank=True, null=True)
    last_communication = models.DateTimeField(blank=True, null=True)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "partner_university"
