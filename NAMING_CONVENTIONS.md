# 📋 Naming Conventions Guide - ProEnglish System

## 🎯 Overview

This document establishes consistent naming conventions across the ProEnglish Django backend system to improve code readability, maintainability, and developer experience.

---

## 📁 File and Directory Structure

### Module Organization
```
apps/
├── courses/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py          # Base classes and mixins
│   │   ├── core.py          # Core models (Course, Section, Chapter)
│   │   ├── enrollment.py    # Enrollment and progress models
│   │   ├── transactions.py  # Payment and transaction models
│   │   ├── quizzes.py       # Quiz and assessment models
│   │   └── resources.py     # Resource and file models
│   ├── serializers/
│   │   ├── __init__.py
│   │   ├── core.py          # Core serializers
│   │   ├── enrollment.py    # Enrollment serializers
│   │   └── ...
│   └── views/
│       ├── __init__.py
│       ├── course_views.py  # Course-related views
│       ├── quiz_views.py    # Quiz-related views
│       └── ...
```

### File Naming Rules
- **Python files**: `snake_case.py`
- **Class files**: Descriptive names like `course_views.py`, `user_serializers.py`
- **Test files**: `test_models.py`, `test_views.py`, `test_services.py`
- **Configuration files**: `settings.py`, `urls.py`, `admin.py`

---

## 🏗️ Model Naming Conventions

### Model Classes
```python
# ✅ Good - PascalCase, descriptive
class Course(BaseModel):
class CourseEnrollment(BaseModel): 
class StudentQuizAttempt(BaseModel):
class ChapterResource(BaseModel):

# ❌ Bad - Unclear, abbreviated
class CourseEnrl(BaseModel):
class SQA(BaseModel):
class Rsrc(BaseModel):
```

### Model Fields
```python
# ✅ Good - Clear, consistent
class Course(BaseModel):
    title = models.CharField(...)
    description = models.TextField(...)
    created_at = models.DateTimeField(...)
    is_active = models.BooleanField(...)
    enrollment_count = models.IntegerField(...)

# ❌ Bad - Inconsistent, unclear
class Course(BaseModel):
    course_title = models.CharField(...)  # Redundant prefix
    desc = models.TextField(...)          # Abbreviated
    createdAt = models.DateTimeField(...) # camelCase (not Python style)
    active = models.BooleanField(...)     # Missing is_ prefix for boolean
```

### Foreign Key Relationships
```python
# ✅ Good - Clear relationship names
class Course(BaseModel):
    teacher = models.ForeignKey(User, related_name='taught_courses', ...)
    
class Enrollment(BaseModel):
    course = models.ForeignKey(Course, related_name='enrollments', ...)
    user = models.ForeignKey(User, related_name='enrollments', ...)

# ❌ Bad - Unclear relationships
class Course(BaseModel):
    teacher = models.ForeignKey(User, related_name='courses', ...)  # Ambiguous
```

### Model Properties and Methods
```python
# ✅ Good - Descriptive, consistent prefixes
class Course(BaseModel):
    @property
    def total_chapters(self):         # Quantitative properties
    
    @property 
    def is_published(self):          # Boolean properties with is_
    
    def can_be_accessed_by(self, user):  # Permission methods with can_
    def mark_as_completed(self):          # Action methods with descriptive verbs
    def get_user_progress(self, user):    # Getter methods with get_

# ❌ Bad - Unclear, inconsistent
class Course(BaseModel):
    def chapters(self):              # Should be total_chapters or get_chapters
    def published(self):             # Should be is_published  
    def access(self, user):          # Should be can_be_accessed_by
```

---

## 🔄 Serializer Naming Conventions

### Serializer Classes
```python
# ✅ Good - Purpose-specific names
class CourseListSerializer(serializers.ModelSerializer):    # For list views
class CourseDetailSerializer(serializers.ModelSerializer):  # For detail views  
class CourseCreateSerializer(serializers.ModelSerializer):  # For creation
class CourseUpdateSerializer(serializers.ModelSerializer):  # For updates

# ❌ Bad - Generic, unclear
class CourseSerializer(serializers.ModelSerializer):        # Too generic
class CourseSer(serializers.ModelSerializer):              # Abbreviated
```

### Serializer Fields
```python
# ✅ Good - Match API field names, clear naming
class CourseListSerializer(serializers.ModelSerializer):
    teacherId = serializers.CharField(source='teacher.id', read_only=True)
    total_enrollments = serializers.ReadOnlyField()
    is_enrolled = serializers.SerializerMethodField()

# ❌ Bad - Inconsistent with API
class CourseListSerializer(serializers.ModelSerializer):
    teacher_id = serializers.CharField(...)  # Should match Express API format
```

### Serializer Methods
```python
# ✅ Good - Clear method naming
class CourseDetailSerializer(serializers.ModelSerializer):
    def get_total_chapters(self, obj):       # get_ prefix for SerializerMethodField
    def validate_price(self, value):         # validate_ prefix for field validation
    def create(self, validated_data):        # Standard DRF method names
    
    @classmethod
    def optimize_queryset(cls, queryset):    # Class methods for optimization
```

---

## 🔍 View Naming Conventions

### View Classes
```python
# ✅ Good - RESTful, descriptive names
class CourseListCreateView(generics.ListCreateAPIView):
class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
class ChapterCommentListCreateView(generics.ListCreateAPIView):

# ❌ Bad - Unclear purpose
class CourseView(APIView):
class ChapterView(APIView):
```

### View Methods
```python
# ✅ Good - Standard DRF method names with clear helpers
class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    def retrieve(self, request, *args, **kwargs):
    def update(self, request, *args, **kwargs):
    def destroy(self, request, *args, **kwargs):
    
    def get_queryset(self):              # Standard DRF helper methods
    def get_serializer_class(self):
    def perform_create(self, serializer):
    
    def check_course_access(self, course, user):  # Custom helper methods
```

### Function-Based Views
```python
# ✅ Good - Verb-based names, clear purpose
@api_view(['POST'])
def create_course_enrollment(request, course_id):

@api_view(['GET'])  
def get_user_course_progress(request, user_id, course_id):

# ❌ Bad - Unclear action
@api_view(['POST'])
def enrollment(request, course_id):
```

---

## 🗂️ URL Naming Conventions

### URL Patterns
```python
# ✅ Good - RESTful, hierarchical
urlpatterns = [
    path('courses/', CourseListCreateView.as_view(), name='course_list_create'),
    path('courses/<uuid:courseId>/', CourseDetailView.as_view(), name='course_detail'),
    path('courses/<uuid:courseId>/sections/', SectionListCreateView.as_view(), name='section_list_create'),
    path('courses/chapters/<uuid:chapterId>/comments/', ChapterCommentListView.as_view(), name='chapter_comments'),
]

# ❌ Bad - Inconsistent, unclear hierarchy  
urlpatterns = [
    path('course/', CourseListCreateView.as_view(), name='courses'),
    path('course-detail/<uuid:id>/', CourseDetailView.as_view(), name='course'),
]
```

### URL Name Conventions
```python
# ✅ Good - Consistent patterns
name='course_list_create'        # model_action
name='course_detail'            # model_view_type
name='chapter_comments'         # resource_subresource
name='user_course_progress'     # user_resource_attribute

# ❌ Bad - Inconsistent
name='courses'                  # Too generic
name='courseDetail'            # camelCase
name='course-detail-view'      # Redundant suffixes
```

---

## 🔧 Service and Utility Naming

### Service Classes
```python
# ✅ Good - Service suffix, clear purpose
class CourseEnrollmentService:
    def enroll_user_in_course(self, user, course):
    def check_enrollment_eligibility(self, user, course):

class PaymentProcessingService:
    def process_course_payment(self, user, course, payment_data):
    def handle_payment_webhook(self, webhook_data):

# ❌ Bad - Unclear purpose
class CourseHandler:
class PaymentManager:
```

### Utility Functions
```python
# ✅ Good - Clear, descriptive names
def calculate_course_progress_percentage(completed_chapters, total_chapters):
def format_duration_for_display(seconds):
def generate_course_certificate_data(user, course):

# ❌ Bad - Abbreviated, unclear
def calc_progress(c, t):
def format_dur(s):
def gen_cert(u, c):
```

---

## 📝 Variable and Parameter Naming

### Function Parameters
```python
# ✅ Good - Descriptive, unambiguous
def update_user_course_progress(user_id, course_id, progress_data):
def send_course_completion_email(student, course, completion_date):

# ❌ Bad - Abbreviated, unclear
def update_progress(uid, cid, data):
def send_email(u, c, d):
```

### Local Variables
```python
# ✅ Good - Clear, contextual
def get_course_statistics(course):
    total_students = course.enrollments.count()
    completion_rate = calculate_completion_rate(course)
    average_progress = calculate_average_progress(course)
    
    return {
        'total_students': total_students,
        'completion_rate': completion_rate, 
        'average_progress': average_progress
    }

# ❌ Bad - Generic, unclear
def get_course_statistics(course):
    count = course.enrollments.count()
    rate = calculate_completion_rate(course)  
    avg = calculate_average_progress(course)
```

---

## 🏷️ Constants and Choices

### Model Choices
```python
# ✅ Good - Descriptive, grouped in classes
class CourseChoices:
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'), 
        ('advanced', 'Advanced'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

# ❌ Bad - Scattered, unclear grouping
LEVELS = [('beg', 'Beginner'), ('int', 'Intermediate')]
COURSE_STATUS = [('d', 'Draft'), ('p', 'Published')]
```

### Configuration Constants
```python
# ✅ Good - Grouped, descriptive
class CourseSettings:
    DEFAULT_PAGE_SIZE = 12
    MAX_CHAPTERS_PER_SECTION = 50
    COURSE_COMPLETION_THRESHOLD = 0.8
    
class QuizSettings:
    DEFAULT_TIME_LIMIT = 1800  # 30 minutes in seconds
    MAX_ATTEMPTS_ALLOWED = 3
    PASSING_SCORE_THRESHOLD = 70

# ❌ Bad - Scattered, unclear
PAGE_SIZE = 12
MAX_CHAP = 50
THRESHOLD = 0.8
```

---

## 📊 Database Naming Conventions

### Table Names
```python
# ✅ Good - Plural, descriptive (set in Meta)
class Course(BaseModel):
    class Meta:
        db_table = 'courses'

class CourseEnrollment(BaseModel):
    class Meta:
        db_table = 'course_enrollments'

# ❌ Bad - Inconsistent
class Course(BaseModel):
    class Meta:
        db_table = 'course'  # Should be plural

class Enrollment(BaseModel):
    class Meta:
        db_table = 'enrollment_table'  # Redundant suffix
```

### Index Names
```python
# ✅ Good - Descriptive, consistent pattern
class Meta:
    indexes = [
        models.Index(fields=['status', 'category'], name='course_status_category_idx'),
        models.Index(fields=['teacher', 'status'], name='course_teacher_status_idx'),
        models.Index(fields=['created_at'], name='course_created_at_idx'),
    ]

# ❌ Bad - Unclear, inconsistent
class Meta:
    indexes = [
        models.Index(fields=['status', 'category'], name='idx_sc'),
        models.Index(fields=['teacher'], name='teacher_index'),
    ]
```

---

## 🧪 Testing Naming Conventions

### Test Classes
```python
# ✅ Good - Clear test scope
class CourseModelTests(TestCase):
class CourseEnrollmentViewTests(APITestCase):
class PaymentServiceTests(TestCase):

# ❌ Bad - Unclear scope  
class CourseTests(TestCase):
class TestCourse(TestCase):
```

### Test Methods
```python
# ✅ Good - Descriptive test scenarios
class CourseModelTests(TestCase):
    def test_course_creation_with_valid_data(self):
    def test_course_cannot_be_enrolled_when_inactive(self):
    def test_calculate_progress_percentage_returns_correct_value(self):
    
# ❌ Bad - Unclear what is being tested
class CourseModelTests(TestCase):  
    def test_course(self):
    def test_enrollment(self):
```

---

## ✅ Validation and Error Handling

### Exception Classes
```python
# ✅ Good - Specific, descriptive exceptions
class CourseEnrollmentError(Exception):
    """Raised when there's an issue with course enrollment."""
    
class PaymentProcessingError(Exception):
    """Raised when payment processing fails."""
    
class QuizSubmissionError(Exception):
    """Raised when quiz submission is invalid."""

# ❌ Bad - Generic exceptions
class CourseError(Exception):
class Error(Exception):
```

### Validation Methods
```python
# ✅ Good - Clear validation purpose
def validate_course_enrollment_eligibility(user, course):
def validate_quiz_submission_data(quiz_data):
def validate_payment_amount(amount, course):

# ❌ Bad - Generic validation
def validate(data):
def check(user, course):
```

---

## 📚 Documentation Naming

### Docstring Conventions
```python
# ✅ Good - Clear, consistent documentation
class Course(BaseModel):
    """
    Course model representing an English course.
    
    This model handles course creation, management, and student enrollment.
    Maps from Express/DynamoDB Course model with the same structure.
    """
    
    def enroll_student(self, student):
        """
        Enroll a student in this course.
        
        Args:
            student (User): The student to enroll
            
        Returns:
            CourseEnrollment: The created enrollment record
            
        Raises:
            CourseEnrollmentError: If enrollment is not allowed
        """
```

---

## 🔄 Migration Naming

### Migration File Names
```python
# ✅ Good - Descriptive migration names
0001_create_course_models.py
0002_add_quiz_functionality.py
0003_add_performance_indexes.py
0004_update_user_roles_for_proenglish.py

# ❌ Bad - Generic, unclear
0001_initial.py
0002_auto_20231201_1234.py
```

---

## 📋 Summary Checklist

### ✅ Model Naming
- [ ] Model classes use PascalCase
- [ ] Field names use snake_case
- [ ] Boolean fields start with `is_` or `has_`
- [ ] Foreign keys have clear `related_name`
- [ ] Methods have descriptive names with appropriate prefixes

### ✅ View Naming  
- [ ] View classes indicate their purpose (List, Detail, Create)
- [ ] Function-based views use verb-action naming
- [ ] Helper methods have clear, descriptive names

### ✅ URL Naming
- [ ] URLs follow RESTful conventions
- [ ] URL names use consistent patterns
- [ ] Parameter names match expected formats

### ✅ General Conventions
- [ ] Constants are grouped in classes
- [ ] Service classes have Service suffix
- [ ] Test classes clearly indicate scope
- [ ] Documentation is clear and consistent

---

**🎯 Goal: Consistent, maintainable, and self-documenting code across the entire ProEnglish system.**