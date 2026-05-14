from django.db import models

class Faculty(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'faculty'

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'department'
        unique_together = ('code', 'faculty')

    def __str__(self):
        return f"{self.name} ({self.code})"

class Promotion(models.Model):
    name = models.CharField(max_length=255)
    year = models.IntegerField()
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    fee_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    threshold_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'promotion'
        unique_together = ('year', 'department')

    def __str__(self):
        return f"{self.name} ({self.year})"

class AcademicYear(models.Model):
    year_name = models.CharField(max_length=50, unique=True)
    threshold_amount = models.DecimalField(max_digits=15, decimal_places=2)
    final_fee = models.DecimalField(max_digits=15, decimal_places=2)
    partial_valid_days = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'academic_year'

    def __str__(self):
        return self.year_name

class Student(models.Model):
    student_number = models.CharField(max_length=50, unique=True)
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    passport_photo_path = models.CharField(max_length=512, blank=True)
    passport_photo_blob = models.BinaryField(blank=True)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True)
    password_hash = models.CharField(max_length=255)
    face_encoding = models.BinaryField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student'

    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.student_number})"

class FaceTrainingPhoto(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    photo_path = models.CharField(max_length=512, blank=True)
    photo_blob = models.BinaryField(blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'face_training_photos'

    def __str__(self):
        return f"Photo for {self.student}"

class FinanceProfile(models.Model):
    ACCESS_CODE_TYPES = [
        ('full', 'Full'),
        ('partial', 'Partial'),
    ]

    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    threshold_required = models.DecimalField(max_digits=10, decimal_places=2)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    is_eligible = models.BooleanField(default=False)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True)
    access_code_issued_at = models.DateTimeField(null=True, blank=True)
    access_code_expires_at = models.DateTimeField(null=True, blank=True)
    access_code_type = models.CharField(max_length=10, choices=ACCESS_CODE_TYPES, null=True, blank=True)
    final_fee = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_profile'

    def __str__(self):
        return f"Finance for {self.student}"

class AccessLog(models.Model):
    STATUS_CHOICES = [
        ('GRANTED', 'Granted'),
        ('DENIED_PASSWORD', 'Denied - Password'),
        ('DENIED_FACE', 'Denied - Face'),
        ('DENIED_FINANCE', 'Denied - Finance'),
        ('DENIED_MULTIPLE', 'Denied - Multiple'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    access_point = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    password_validated = models.BooleanField(default=False)
    face_validated = models.BooleanField(default=False)
    finance_validated = models.BooleanField(default=False)
    ip_address = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'access_log'

    def __str__(self):
        return f"Access {self.status} for {self.student} at {self.created_at}"
