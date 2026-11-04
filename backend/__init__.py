import os
import sys

_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Polyfill 'packaging' for langchain_core/langgraph if not installed as standalone top-level package
if 'packaging' not in sys.modules:
    try:
        import packaging
    except ImportError:
        for vendor_prefix in ['setuptools._vendor.packaging', 'pip._vendor.packaging']:
            try:
                base = __import__(vendor_prefix, fromlist=['packaging'])
                sys.modules['packaging'] = base
                for sub in ['version', 'specifiers', 'requirements', 'markers', 'tags', 'utils']:
                    try:
                        smod = __import__(f'{vendor_prefix}.{sub}', fromlist=[sub])
                        sys.modules[f'packaging.{sub}'] = smod
                    except Exception:
                        pass
                break
            except Exception:
                pass

