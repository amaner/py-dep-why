import pytest
from py_dep_why.normalize import normalize_name


def test_normalize_underscore():
    """Test that underscores are replaced with dashes."""
    assert normalize_name("Foo_Bar") == "foo-bar"


def test_normalize_dot():
    """Test that dots are replaced with dashes."""
    assert normalize_name("foo.bar") == "foo-bar"


def test_normalize_double_dash():
    """Test that runs of dashes are collapsed to a single dash."""
    assert normalize_name("foo--bar") == "foo-bar"


def test_normalize_mixed_separators():
    """Test that mixed separators are all replaced with a single dash."""
    assert normalize_name("foo._-bar") == "foo-bar"
    assert normalize_name("foo_._bar") == "foo-bar"


def test_normalize_lowercase():
    """Test that names are lowercased."""
    assert normalize_name("FooBar") == "foobar"
    assert normalize_name("FOOBAR") == "foobar"


def test_normalize_whitespace():
    """Test that leading/trailing whitespace is stripped."""
    assert normalize_name("  foo-bar  ") == "foo-bar"
    assert normalize_name("\tfoo-bar\n") == "foo-bar"


def test_normalize_already_normalized():
    """Test that already normalized names pass through unchanged."""
    assert normalize_name("foo-bar") == "foo-bar"
    assert normalize_name("requests") == "requests"


def test_normalize_complex():
    """Test complex real-world package names."""
    assert normalize_name("Django_REST_Framework") == "django-rest-framework"
    assert normalize_name("Pillow") == "pillow"
    assert normalize_name("scikit-learn") == "scikit-learn"
    assert normalize_name("beautifulsoup4") == "beautifulsoup4"
