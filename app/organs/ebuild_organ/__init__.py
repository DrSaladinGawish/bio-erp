"""
Ebuild System Organ v1.0.0
Universal ERP Meta-Builder for Bio-ERP
Category: sys-tools/ebuild
"""
__version__ = "1.0.0"
__organ__ = "ebuild-system"

from .sub_app import ebuild_app

__all__ = ["ebuild_app", "__version__"]
