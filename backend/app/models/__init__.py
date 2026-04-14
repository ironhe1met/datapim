"""SQLAlchemy models — imported here so Alembic autogenerate sees metadata."""

from app.models.ai_review import AIReview
from app.models.ai_task import AITask
from app.models.base import Base
from app.models.category import Category
from app.models.import_log import ImportLog
from app.models.product import Product
from app.models.product_attribute import ProductAttribute
from app.models.product_image import ProductImage
from app.models.user import User

__all__ = [
    "AIReview",
    "AITask",
    "Base",
    "Category",
    "ImportLog",
    "Product",
    "ProductAttribute",
    "ProductImage",
    "User",
]
