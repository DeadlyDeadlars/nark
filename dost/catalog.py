import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


CATALOG_FILE = os.getenv("PRODUCTS_FILE", "products.txt")


@dataclass
class ProductVariant:
    weight: str
    price: float


@dataclass
class CatalogItem:
    name: str
    variants: List[ProductVariant]


def _parse_line(line: str) -> Optional[Tuple[str, str, float]]:
    parts = [p.strip() for p in line.strip().split(":")]
    if len(parts) != 3:
        return None
    name, weight, price_str = parts
    if not name or not weight:
        return None
    try:
        price = float(price_str.replace(",", "."))
    except ValueError:
        return None
    return name, weight, price


def load_catalog(file_path: Optional[str] = None) -> List[CatalogItem]:
    path = file_path or CATALOG_FILE
    if not os.path.exists(path):
        return []

    name_to_variants: Dict[str, List[ProductVariant]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            if not raw.strip() or raw.strip().startswith("#"):
                continue
            parsed = _parse_line(raw)
            if not parsed:
                continue
            name, weight, price = parsed
            name_to_variants.setdefault(name, []).append(ProductVariant(weight=weight, price=price))

    catalog: List[CatalogItem] = []
    for name, variants in name_to_variants.items():
        catalog.append(CatalogItem(name=name, variants=variants))
    return catalog


def get_product_names(file_path: Optional[str] = None) -> List[str]:
    return [item.name for item in load_catalog(file_path)]


def get_variants_for_product(product_name: str, file_path: Optional[str] = None) -> List[ProductVariant]:
    for item in load_catalog(file_path):
        if item.name == product_name:
            return item.variants
    return []


def get_variant(product_name: str, variant_index: int, file_path: Optional[str] = None) -> Optional[ProductVariant]:
    variants = get_variants_for_product(product_name, file_path)
    if 0 <= variant_index < len(variants):
        return variants[variant_index]
    return None


