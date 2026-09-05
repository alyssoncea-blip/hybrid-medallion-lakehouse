"""
Test Snowpark UDFs locally (without Snowflake connection).
Run: pytest src/snowpark/tests/test_udfs.py -v
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from src.snowpark.udfs.feature_udfs import (
    price_bucket_udf,
    normalize_price_udf,
    category_flag_udf,
    sku_numeric_suffix_udf,
    name_complexity_udf,
)


class TestPriceBucketUDF:
    def test_low_price(self):
        assert price_bucket_udf(25.0) == "LOW"
        assert price_bucket_udf(49.99) == "LOW"
    
    def test_medium_price(self):
        assert price_bucket_udf(50.0) == "MEDIUM"
        assert price_bucket_udf(199.99) == "MEDIUM"
    
    def test_high_price(self):
        assert price_bucket_udf(200.0) == "HIGH"
        assert price_bucket_udf(499.99) == "HIGH"
    
    def test_premium_price(self):
        assert price_bucket_udf(500.0) == "PREMIUM"
        assert price_bucket_udf(1000.0) == "PREMIUM"
    
    def test_none_price(self):
        assert price_bucket_udf(None) == "UNKNOWN"


class TestNormalizePriceUDF:
    def test_normal_case(self):
        # price=150, min=50, max=250 -> (150-50)/(250-50) = 100/200 = 0.5
        result = normalize_price_udf(150.0, 50.0, 250.0)
        assert result == 0.5
    
    def test_at_min(self):
        result = normalize_price_udf(50.0, 50.0, 250.0)
        assert result == 0.0
    
    def test_at_max(self):
        result = normalize_price_udf(250.0, 50.0, 250.0)
        assert result == 1.0
    
    def test_equal_min_max(self):
        # Edge case: min == max
        result = normalize_price_udf(100.0, 100.0, 100.0)
        assert result == 0.5
    
    def test_none_inputs(self):
        assert normalize_price_udf(None, 50.0, 250.0) is None
        assert normalize_price_udf(100.0, None, 250.0) is None
        assert normalize_price_udf(100.0, 50.0, None) is None


class TestCategoryFlagUDF:
    def test_match(self):
        assert category_flag_udf("ELETRONICOS", "ELETRONICOS") == 1
        assert category_flag_udf("  ELETRONICOS  ", "ELETRONICOS") == 1
    
    def test_no_match(self):
        assert category_flag_udf("MOVEIS", "ELETRONICOS") == 0
        assert category_flag_udf("", "ELETRONICOS") == 0
    
    def test_none_inputs(self):
        assert category_flag_udf(None, "ELETRONICOS") == 0
        assert category_flag_udf("ELETRONICOS", None) == 0


class TestSKUNumericSuffixUDF:
    def test_with_suffix(self):
        assert sku_numeric_suffix_udf("PROD-001") == 1
        assert sku_numeric_suffix_udf("ITEM-12345") == 12345
        assert sku_numeric_suffix_udf("ABC123") == 123
    
    def test_without_suffix(self):
        assert sku_numeric_suffix_udf("PROD-ABC") is None
        assert sku_numeric_suffix_udf("ABC") is None
    
    def test_empty(self):
        assert sku_numeric_suffix_udf("") is None
        assert sku_numeric_suffix_udf(None) is None


class TestNameComplexityUDF:
    def test_normal(self):
        assert name_complexity_udf("Produto Teste") == 13
        # name_complexity_udf strips whitespace: "  Espacos  " -> "Espacos" -> 7
        assert name_complexity_udf("  Espacos  ") == 7
    
    def test_empty(self):
        assert name_complexity_udf("") == 0
        assert name_complexity_udf(None) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])