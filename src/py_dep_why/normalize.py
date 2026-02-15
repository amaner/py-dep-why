import re


def normalize_name(name: str) -> str:
    """
    Normalize a package name according to PEP 503.
    
    - Lowercase the name
    - Replace runs of [-_.] with a single dash
    - Strip leading/trailing whitespace
    
    Args:
        name: Package name to normalize
        
    Returns:
        Normalized package name
        
    Examples:
        >>> normalize_name("Foo_Bar")
        'foo-bar'
        >>> normalize_name("foo.bar")
        'foo-bar'
        >>> normalize_name("foo--bar")
        'foo-bar'
    """
    name = name.strip()
    name = name.lower()
    name = re.sub(r"[-_.]+", "-", name)
    return name
