"""
Custom pagination classes for course API endpoints.

Optimized pagination with performance considerations and consistent response format.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for most list endpoints.
    Provides consistent pagination with performance optimizations.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        """
        Return paginated response in consistent format.
        """
        return Response(OrderedDict([
            ('message', 'Dados recuperados com sucesso'),
            ('data', OrderedDict([
                ('count', self.page.paginator.count),
                ('next', self.get_next_link()),
                ('previous', self.get_previous_link()),
                ('current_page', self.page.number),
                ('total_pages', self.page.paginator.num_pages),
                ('page_size', self.get_page_size(self.request)),
                ('results', data)
            ]))
        ]))


class LargePaginatedList(PageNumberPagination):
    """
    Pagination for large datasets like comments, transactions, etc.
    Smaller page size for better performance.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    page_query_param = 'page'

    def get_paginated_response(self, data):
        """
        Return paginated response in consistent format.
        """
        return Response(OrderedDict([
            ('message', 'Dados recuperados com sucesso'),
            ('data', OrderedDict([
                ('count', self.page.paginator.count),
                ('next', self.get_next_link()),
                ('previous', self.get_previous_link()),
                ('current_page', self.page.number),
                ('total_pages', self.page.paginator.num_pages),
                ('page_size', self.get_page_size(self.request)),
                ('results', data)
            ]))
        ]))


class CourseListPagination(StandardResultsSetPagination):
    """
    Specialized pagination for course listings.
    Includes additional metadata for course filtering.
    """
    page_size = 12  # Good for grid layouts (3x4, 4x3, 2x6, etc.)
    
    def get_paginated_response(self, data):
        """
        Enhanced response with course-specific metadata.
        """
        # Calculate category counts if available in context
        extra_data = {}
        
        if hasattr(self, 'context') and self.context:
            request = self.context.get('request')
            if request and hasattr(request, 'category_counts'):
                extra_data['category_counts'] = request.category_counts
        
        data_dict = OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('current_page', self.page.number),
            ('total_pages', self.page.paginator.num_pages),
            ('page_size', self.get_page_size(self.request)),
            ('results', data)
        ])
        data_dict.update(extra_data)
        
        return Response(OrderedDict([
            ('message', 'Cursos recuperados com sucesso'),
            ('data', data_dict)
        ]))


class TransactionListPagination(LargePaginatedList):
    """
    Pagination for transaction history.
    Ordered by most recent first with better performance for large lists.
    """
    page_size = 15
    
    def get_paginated_response(self, data):
        """
        Transaction-specific response with financial metadata.
        """
        extra_data = {}
        
        # Add transaction summary if available
        if hasattr(self, 'context') and self.context:
            request = self.context.get('request')
            if request and hasattr(request, 'transaction_summary'):
                extra_data['summary'] = request.transaction_summary
        
        data_dict = OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('current_page', self.page.number),
            ('total_pages', self.page.paginator.num_pages),
            ('page_size', self.get_page_size(self.request)),
            ('results', data)
        ])
        data_dict.update(extra_data)
        
        return Response(OrderedDict([
            ('message', 'Transações recuperadas com sucesso'),
            ('data', data_dict)
        ]))


class CommentListPagination(LargePaginatedList):
    """
    Pagination for chapter comments and other discussion content.
    Optimized for real-time updates.
    """
    page_size = 20  # Comments are usually shorter, can fit more per page
    
    def get_paginated_response(self, data):
        """
        Comment-specific response format.
        """
        return Response(OrderedDict([
            ('message', 'Comentários recuperados com sucesso'),
            ('data', OrderedDict([
                ('count', self.page.paginator.count),
                ('next', self.get_next_link()),
                ('previous', self.get_previous_link()),
                ('current_page', self.page.number),
                ('total_pages', self.page.paginator.num_pages),
                ('page_size', self.get_page_size(self.request)),
                ('results', data)
            ]))
        ]))


class QuizAttemptPagination(LargePaginatedList):
    """
    Pagination for quiz attempts and progress tracking.
    """
    page_size = 25  # Good for progress tracking views
    
    def get_paginated_response(self, data):
        """
        Quiz attempt response with performance metadata.
        """
        extra_data = {}
        
        # Add performance summary if available
        if hasattr(self, 'context') and self.context:
            request = self.context.get('request')
            if request and hasattr(request, 'performance_summary'):
                extra_data['performance_summary'] = request.performance_summary
        
        data_dict = OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('current_page', self.page.number),
            ('total_pages', self.page.paginator.num_pages),
            ('page_size', self.get_page_size(self.request)),
            ('results', data)
        ])
        data_dict.update(extra_data)
        
        return Response(OrderedDict([
            ('message', 'Tentativas de quiz recuperadas com sucesso'),
            ('data', data_dict)
        ]))


# Utility functions for pagination optimization

def optimize_paginated_queryset(queryset, request, default_ordering=None):
    """
    Apply common optimizations to paginated querysets.
    
    Args:
        queryset: Django QuerySet to optimize
        request: HTTP request object
        default_ordering: Default ordering if none specified
    
    Returns:
        Optimized QuerySet
    """
    # Apply ordering
    ordering = request.query_params.get('ordering', default_ordering)
    if ordering:
        # Validate ordering field to prevent injection
        allowed_orderings = [
            'created_at', '-created_at',
            'updated_at', '-updated_at',
            'title', '-title',
            'price', '-price',
            'level', '-level',
            'category', '-category',
            'status', '-status'
        ]
        if ordering in allowed_orderings:
            queryset = queryset.order_by(ordering)
        elif default_ordering:
            queryset = queryset.order_by(default_ordering)
    elif default_ordering:
        queryset = queryset.order_by(default_ordering)
    
    return queryset


def add_pagination_context(paginator, context_data=None):
    """
    Add additional context data to pagination response.
    
    Args:
        paginator: Pagination instance
        context_data: Dictionary of additional context data
    
    Returns:
        None (modifies paginator in place)
    """
    if context_data and hasattr(paginator, 'context'):
        paginator.context.update(context_data)
    elif context_data:
        paginator.context = context_data