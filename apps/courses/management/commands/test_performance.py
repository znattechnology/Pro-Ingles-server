"""
Django management command to test and benchmark course API performance.

Usage:
    python manage.py test_performance
    python manage.py test_performance --benchmark
    python manage.py test_performance --check-n-plus-one
"""

import time
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.courses.models import Course, CourseSection, Chapter, CourseEnrollment, Transaction
from apps.courses.views import CourseListCreateView, CourseDetailView
from apps.courses.serializers import CourseListSerializer, CourseDetailSerializer


User = get_user_model()


class Command(BaseCommand):
    help = 'Test and benchmark course API performance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--benchmark',
            action='store_true',
            help='Run comprehensive performance benchmarks',
        )
        parser.add_argument(
            '--check-n-plus-one',
            action='store_true',
            help='Check for N+1 query problems',
        )
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='Create test data for performance testing',
        )
        parser.add_argument(
            '--test-endpoints',
            action='store_true',
            help='Test API endpoint performance',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Performance Testing for Course API')
        )
        
        if options.get('create_test_data'):
            self.create_test_data()
        
        if options.get('check_n_plus_one'):
            self.check_n_plus_one_queries()
        
        if options.get('benchmark'):
            self.run_benchmarks()
        
        if options.get('test_endpoints'):
            self.test_api_endpoints()
        
        if not any([options.get('benchmark'), options.get('check_n_plus_one'), 
                   options.get('create_test_data'), options.get('test_endpoints')]):
            self.run_basic_tests()
    
    def create_test_data(self):
        """Create test data for performance testing."""
        self.stdout.write("Creating test data...")
        
        with transaction.atomic():
            # Create test users
            for i in range(5):
                teacher, created = User.objects.get_or_create(
                    email=f'teacher{i}@test.com',
                    defaults={
                        'name': f'Test Teacher {i}',
                        'role': 'teacher',
                        'is_active': True
                    }
                )
                
                # Create courses for each teacher
                for j in range(3):
                    course, created = Course.objects.get_or_create(
                        title=f'Test Course {i}-{j}',
                        teacher=teacher,
                        defaults={
                            'description': f'Test course description for {i}-{j}',
                            'category': 'Test Category',
                            'level': 'Beginner',
                            'status': 'Published',
                            'price': 50.00
                        }
                    )
                    
                    if created:
                        # Create sections
                        for k in range(2):
                            section = CourseSection.objects.create(
                                course=course,
                                sectionTitle=f'Section {k+1}',
                                sectionDescription=f'Test section {k+1}',
                                order=k+1
                            )
                            
                            # Create chapters
                            for l in range(3):
                                Chapter.objects.create(
                                    section=section,
                                    title=f'Chapter {l+1}',
                                    content=f'Test content for chapter {l+1}',
                                    type='Text',
                                    order=l+1
                                )
        
        self.stdout.write(
            self.style.SUCCESS('Test data created successfully')
        )
    
    def check_n_plus_one_queries(self):
        """Check for N+1 query problems in common operations."""
        self.stdout.write("Checking for N+1 query problems...")
        
        # Test course list with enrollments
        self.stdout.write("Testing course list performance...")
        
        # Without optimization
        connection.queries_log.clear()
        start_queries = len(connection.queries)
        
        courses = Course.objects.filter(status='Published')[:10]
        for course in courses:
            _ = course.total_enrollments  # This might cause N+1
            _ = course.total_chapters     # This might cause N+1
        
        unoptimized_queries = len(connection.queries) - start_queries
        
        # With optimization (using optimized serializer)
        connection.queries_log.clear()
        start_queries = len(connection.queries)
        
        optimized_courses = CourseListSerializer.optimize_queryset(
            Course.objects.filter(status='Published')[:10],
            include_enrollment_count=True
        )
        
        for course in optimized_courses:
            _ = course._enrollment_count if hasattr(course, '_enrollment_count') else course.total_enrollments
            _ = course.total_chapters
        
        optimized_queries = len(connection.queries) - start_queries
        
        self.stdout.write(
            f"Course list queries - Unoptimized: {unoptimized_queries}, "
            f"Optimized: {optimized_queries}"
        )
        
        if unoptimized_queries > optimized_queries:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Optimization working! Reduced from {unoptimized_queries} to {optimized_queries} queries")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"⚠ Optimization might not be effective")
            )
    
    def run_benchmarks(self):
        """Run comprehensive performance benchmarks."""
        self.stdout.write("Running performance benchmarks...")
        
        # Test serializer performance
        self.benchmark_serializers()
        
        # Test queryset optimization
        self.benchmark_querysets()
        
        # Test database indexes
        self.benchmark_database_queries()
    
    def benchmark_serializers(self):
        """Benchmark serializer performance."""
        self.stdout.write("Benchmarking serializers...")
        
        courses = Course.objects.filter(status='Published')[:20]
        
        # Test CourseListSerializer
        start_time = time.time()
        serializer = CourseListSerializer(courses, many=True)
        _ = serializer.data
        list_serializer_time = time.time() - start_time
        
        # Test CourseDetailSerializer (more complex)
        course = courses.first()
        if course:
            start_time = time.time()
            detail_serializer = CourseDetailSerializer(course)
            _ = detail_serializer.data
            detail_serializer_time = time.time() - start_time
            
            self.stdout.write(
                f"Serializer performance:\n"
                f"  - List serializer (20 items): {list_serializer_time:.3f}s\n"
                f"  - Detail serializer (1 item): {detail_serializer_time:.3f}s"
            )
    
    def benchmark_querysets(self):
        """Benchmark different queryset optimizations."""
        self.stdout.write("Benchmarking queryset optimizations...")
        
        # Basic queryset
        start_time = time.time()
        basic_courses = list(Course.objects.filter(status='Published')[:10])
        basic_time = time.time() - start_time
        
        # Optimized queryset
        start_time = time.time()
        optimized_courses = list(
            CourseListSerializer.optimize_queryset(
                Course.objects.filter(status='Published')[:10],
                include_enrollment_count=True
            )
        )
        optimized_time = time.time() - start_time
        
        self.stdout.write(
            f"Queryset performance:\n"
            f"  - Basic queryset: {basic_time:.3f}s\n"
            f"  - Optimized queryset: {optimized_time:.3f}s"
        )
    
    def benchmark_database_queries(self):
        """Benchmark database query performance with indexes."""
        self.stdout.write("Benchmarking database queries...")
        
        # Test filtering by different fields
        filters_to_test = [
            {'status': 'Published'},
            {'category': 'Test Category'},
            {'level': 'Beginner'},
            {'status': 'Published', 'category': 'Test Category'},
            {'teacher__role': 'teacher', 'status': 'Published'}
        ]
        
        for i, filter_params in enumerate(filters_to_test):
            start_time = time.time()
            connection.queries_log.clear()
            start_queries = len(connection.queries)
            
            results = list(Course.objects.filter(**filter_params)[:5])
            
            end_time = time.time()
            end_queries = len(connection.queries)
            
            query_time = end_time - start_time
            query_count = end_queries - start_queries
            
            self.stdout.write(
                f"  Filter {i+1} {filter_params}: {len(results)} results, "
                f"{query_count} queries, {query_time:.3f}s"
            )
    
    def test_api_endpoints(self):
        """Test API endpoint performance."""
        self.stdout.write("Testing API endpoint performance...")
        
        factory = RequestFactory()
        
        # Test course list endpoint
        request = factory.get('/api/v1/courses/')
        start_time = time.time()
        connection.queries_log.clear()
        start_queries = len(connection.queries)
        
        view = CourseListCreateView.as_view()
        response = view(request)
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        list_time = end_time - start_time
        list_queries = end_queries - start_queries
        
        self.stdout.write(
            f"Course list endpoint: {response.status_code} status, "
            f"{list_queries} queries, {list_time:.3f}s"
        )
        
        # Test course detail endpoint
        course = Course.objects.filter(status='Published').first()
        if course:
            request = factory.get(f'/api/v1/courses/{course.id}/')
            start_time = time.time()
            connection.queries_log.clear()
            start_queries = len(connection.queries)
            
            view = CourseDetailView.as_view()
            response = view(request, courseId=course.id)
            
            end_time = time.time()
            end_queries = len(connection.queries)
            
            detail_time = end_time - start_time
            detail_queries = end_queries - start_queries
            
            self.stdout.write(
                f"Course detail endpoint: {response.status_code} status, "
                f"{detail_queries} queries, {detail_time:.3f}s"
            )
    
    def run_basic_tests(self):
        """Run basic performance tests."""
        self.stdout.write("Running basic performance tests...")
        
        # Check database connectivity
        try:
            course_count = Course.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Database connected. Found {course_count} courses.")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Database connection failed: {e}")
            )
            return
        
        # Check if indexes exist
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'courses' AND schemaname = 'public'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        expected_indexes = [
            'course_status_category_idx',
            'course_teacher_status_idx',
            'course_status_date_idx',
            'course_category_level_idx'
        ]
        
        for index in expected_indexes:
            if index in indexes:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Index {index} exists")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Index {index} missing")
                )
        
        self.stdout.write(
            self.style.SUCCESS("Basic performance tests completed")
        )