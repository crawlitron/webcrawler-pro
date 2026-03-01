"""
Basic health and import tests for WebCrawler Pro backend.
Tests are designed to work with or without full dependencies installed.
"""
import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_python_version():
    """Ensure Python 3.11+"""
    assert sys.version_info >= (3, 11)


def test_app_imports():
    """Test critical imports work (requires sqlalchemy)"""
    sqlalchemy = pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed")
    from app.database import Base
    from app.models import Project, Crawl, Page
    assert Base is not None


def test_schemas_import():
    """Test schemas import (requires sqlalchemy)"""
    pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed")
    import app.schemas as schemas
    assert hasattr(schemas, 'ProjectCreate')


def test_analyzer_import():
    """Test analyzer import"""
    from app.crawler.analyzer import SEOAnalyzer
    analyzer = SEOAnalyzer()
    assert analyzer is not None


def test_analyzer_has_required_methods():
    """Test SEOAnalyzer has all required methods"""
    from app.crawler.analyzer import SEOAnalyzer
    analyzer = SEOAnalyzer()
    required_methods = [
        'analyze',
        'analyze_images',
        'analyze_redirects',
        'analyze_accessibility',
        'analyze_keywords',
        'analyze_mobile_seo',
    ]
    for method in required_methods:
        assert hasattr(analyzer, method), f"SEOAnalyzer missing method: {method}"


def test_seo_analysis_basic():
    """Test basic SEO analysis using correct API"""
    from app.crawler.analyzer import SEOAnalyzer

    page = {
        'url': 'https://example.com/test',
        'title': 'Test Page',
        'meta_description': 'A test description for SEO analysis',
        'h1_count': 1,
        'h1_texts': ['Main Heading'],
        'h2_count': 1,
        'h2_texts': ['Sub Heading'],
        'word_count': 150,
        'html_size': 5000,
        'images': [{'src': '/image.jpg', 'alt': 'Test image', 'width': None, 'height': None}],
        'internal_links': [{'url': '/internal', 'text': 'Internal link'}],
        'external_links': [],
        'canonical_url': 'https://example.com/test',
        'robots_meta': '',
        'og_title': 'Test Page OG',
        'og_description': 'OG description',
        'status_code': 200,
        'content_type': 'text/html',
        'has_viewport': True,
        'lang': 'de',
        'schema_markup': False,
        'seo_score': 75,
    }

    analyzer = SEOAnalyzer()
    issues = analyzer.analyze(page)
    assert isinstance(issues, list)


def test_robots_txt_function_import():
    """Test robots_sitemap module has required functions"""
    from app.crawler.robots_sitemap import analyze_robots_txt, analyze_sitemap
    assert callable(analyze_robots_txt)
    assert callable(analyze_sitemap)


def test_crawler_modules_importable():
    """Test all crawler modules can be imported"""
    import app.crawler.analyzer
    import app.crawler.robots_sitemap
    assert True  # If we get here, imports succeeded


def test_cwv_analyzer_importable():
    """Test CWV analyzer module exists and is importable"""
    import app.crawler.cwv_analyzer
    assert True


def test_pdf_generator_importable():
    """Test PDF generator module exists"""
    import app.reports.pdf_generator
    assert True


def test_email_sender_importable():
    """Test email sender module exists"""
    import app.notifications.email_sender
    assert True


class TestSEOAnalyzerMethods:
    """Test SEOAnalyzer method outputs"""

    def _make_page(self, **overrides):
        """Create a base page dict for testing"""
        base = {
            'url': 'https://example.com/',
            'title': 'Perfect SEO Title Here',
            'meta_description': 'This is a perfect meta description that is between 120 and 160 characters long for optimal SEO performance testing.',
            'h1_count': 1,
            'h1_texts': ['Perfect Heading'],
            'h2_count': 2,
            'h2_texts': ['Sub Heading One', 'Sub Heading Two'],
            'word_count': 500,
            'html_size': 10000,
            'images': [{'src': '/img.jpg', 'alt': 'Descriptive alt text', 'width': 800, 'height': 600}],
            'internal_links': [{'url': '/page1', 'text': 'Link One'}],
            'external_links': [{'url': 'https://google.com', 'text': 'Google'}],
            'canonical_url': 'https://example.com/',
            'robots_meta': '',
            'og_title': 'Perfect OG Title',
            'og_description': 'Perfect OG description here',
            'status_code': 200,
            'content_type': 'text/html',
            'has_viewport': True,
            'lang': 'de',
            'schema_markup': True,
            'seo_score': 90,
        }
        base.update(overrides)
        return base

    def test_analyze_returns_list(self):
        from app.crawler.analyzer import SEOAnalyzer
        analyzer = SEOAnalyzer()
        issues = analyzer.analyze(self._make_page())
        assert isinstance(issues, list)

    def test_missing_title_generates_issue(self):
        from app.crawler.analyzer import SEOAnalyzer
        analyzer = SEOAnalyzer()
        page = self._make_page(title='')
        issues = analyzer.analyze(page)
        issue_types = [i.get('issue_type', '') if isinstance(i, dict) else getattr(i, 'issue_type', '') for i in issues]
        assert any('title' in str(t).lower() for t in issue_types)

    def test_missing_h1_generates_issue(self):
        from app.crawler.analyzer import SEOAnalyzer
        analyzer = SEOAnalyzer()
        page = self._make_page(h1_count=0, h1_texts=[])
        issues = analyzer.analyze(page)
        assert len(issues) > 0

    def test_analyze_images_returns_list(self):
        from app.crawler.analyzer import SEOAnalyzer
        analyzer = SEOAnalyzer()
        page = self._make_page(
            images=[
                {'src': '/img1.jpg', 'alt': '', 'width': None, 'height': None},
                {'src': '/img2.jpg', 'alt': 'Good alt', 'width': 800, 'height': 600},
            ]
        )
        issues = analyzer.analyze_images(page)
        assert isinstance(issues, list)

    def test_analyze_keywords_returns_dict(self):
        from app.crawler.analyzer import SEOAnalyzer
        analyzer = SEOAnalyzer()
        page = self._make_page()
        result = analyzer.analyze_keywords(page)
        assert isinstance(result, dict)
