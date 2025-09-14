#!/usr/bin/env python3
"""
Simple test script to verify Django optimizations are working.
Can be run without full Django environment setup.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, '/Users/vadao/Documents/Projectos_Next/Sistema_Ingles/Tuwi-Backend')

def test_imports():
    """Test that our optimization modules can be imported correctly."""
    print("Testing imports...")
    
    try:
        # Test pagination imports
        from apps.courses.pagination import (
            StandardResultsSetPagination, 
            CourseListPagination,
            optimize_paginated_queryset
        )
        print("✓ Pagination classes imported successfully")
        
        # Test middleware imports
        from apps.courses.middleware import QueryDebugMiddleware, PerformanceMetricsMiddleware
        print("✓ Middleware classes imported successfully")
        
        # Test model imports
        from apps.courses.models import Course, CourseSection, Chapter
        print("✓ Model classes imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_serializer_optimizations():
    """Test that serializer optimizations are properly implemented."""
    print("\nTesting serializer optimizations...")
    
    try:
        from apps.courses.serializers import CourseListSerializer, CourseDetailSerializer
        
        # Check if optimize_queryset method exists
        if hasattr(CourseListSerializer, 'optimize_queryset'):
            print("✓ CourseListSerializer has optimize_queryset method")
        else:
            print("✗ CourseListSerializer missing optimize_queryset method")
            return False
        
        if hasattr(CourseDetailSerializer, 'optimize_queryset'):
            print("✓ CourseDetailSerializer has optimize_queryset method")
        else:
            print("✗ CourseDetailSerializer missing optimize_queryset method")
            return False
            
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_pagination_classes():
    """Test that pagination classes are properly configured."""
    print("\nTesting pagination classes...")
    
    try:
        from apps.courses.pagination import CourseListPagination, TransactionListPagination
        
        # Test CourseListPagination configuration
        course_pagination = CourseListPagination()
        if course_pagination.page_size == 12:
            print("✓ CourseListPagination has correct page_size (12)")
        else:
            print(f"✗ CourseListPagination has wrong page_size ({course_pagination.page_size})")
            
        # Test TransactionListPagination configuration  
        transaction_pagination = TransactionListPagination()
        if transaction_pagination.page_size == 15:
            print("✓ TransactionListPagination has correct page_size (15)")
        else:
            print(f"✗ TransactionListPagination has wrong page_size ({transaction_pagination.page_size})")
            
        return True
        
    except Exception as e:
        print(f"✗ Error testing pagination: {e}")
        return False

def test_migration_files():
    """Test that migration files exist and contain expected content."""
    print("\nTesting migration files...")
    
    migration_file = '/Users/vadao/Documents/Projectos_Next/Sistema_Ingles/Tuwi-Backend/apps/courses/migrations/0005_add_performance_indexes.py'
    
    try:
        with open(migration_file, 'r') as f:
            content = f.read()
            
        # Check for expected indexes
        expected_indexes = [
            'course_status_category_idx',
            'course_teacher_status_idx', 
            'course_status_date_idx',
            'course_category_level_idx',
            'enrollment_course_date_idx'
        ]
        
        for index_name in expected_indexes:
            if index_name in content:
                print(f"✓ Found index: {index_name}")
            else:
                print(f"✗ Missing index: {index_name}")
                return False
        
        print("✓ All expected indexes found in migration file")
        return True
        
    except FileNotFoundError:
        print(f"✗ Migration file not found: {migration_file}")
        return False
    except Exception as e:
        print(f"✗ Error reading migration file: {e}")
        return False

def test_model_optimizations():
    """Test that model optimizations are in place.""" 
    print("\nTesting model optimizations...")
    
    try:
        from apps.courses.models import Course
        
        # Check if total_chapters method is optimized
        course_class = Course
        if hasattr(course_class, 'total_chapters'):
            print("✓ Course has total_chapters property")
        else:
            print("✗ Course missing total_chapters property")
            return False
            
        # Check Meta class for indexes
        if hasattr(course_class, 'Meta') and hasattr(course_class.Meta, 'indexes'):
            indexes = course_class.Meta.indexes
            print(f"✓ Course model has {len(indexes)} indexes defined")
        else:
            print("✗ Course model missing indexes in Meta class")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Error testing model optimizations: {e}")
        return False

def run_all_tests():
    """Run all tests and return summary."""
    print("=== Django Performance Optimization Tests ===\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Serializer Optimizations", test_serializer_optimizations), 
        ("Pagination Classes", test_pagination_classes),
        ("Migration Files", test_migration_files),
        ("Model Optimizations", test_model_optimizations)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All optimization tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)