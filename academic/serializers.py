from rest_framework import serializers
from .models import Faculty, Department, Promotion, AcademicYear, Student, FaceTrainingPhoto, FinanceProfile, AccessLog

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'

class DepartmentSerializer(serializers.ModelSerializer):
    faculty = FacultySerializer(read_only=True)
    faculty_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Department
        fields = '__all__'

class PromotionSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Promotion
        fields = '__all__'

class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    promotion = PromotionSerializer(read_only=True)
    promotion_id = serializers.IntegerField(write_only=True)
    academic_year = AcademicYearSerializer(read_only=True)
    academic_year_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Student
        fields = '__all__'
        extra_kwargs = {
            'password_hash': {'write_only': True},
            'face_encoding': {'read_only': True},
        }

class FaceTrainingPhotoSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    student_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FaceTrainingPhoto
        fields = '__all__'

class FinanceProfileSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    student_id = serializers.IntegerField(write_only=True)
    academic_year = AcademicYearSerializer(read_only=True)
    academic_year_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = FinanceProfile
        fields = '__all__'

class AccessLogSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    student_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = AccessLog
        fields = '__all__'