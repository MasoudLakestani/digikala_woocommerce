"""
Property analyzer utility for dynamically determining maximum properties in products
"""
import json
import logging
from typing import Dict, Any, List


logger = logging.getLogger(__name__)


class PropertyAnalyzer:
    """Analyzes product data to determine maximum number of properties"""
    
    def __init__(self):
        self.max_properties = 0
        self.analyzed_products = 0
    
    def analyze_product_properties(self, product_data: Dict[str, Any]) -> int:
        """
        Analyze a single product to count its properties
        Returns the number of properties found in this product
        """
        property_count = 0
        
        if isinstance(product_data, dict):
            # Handle Digikala API structure: specifications[]['attributes'][]
            specifications = product_data.get('specifications', [])
            
            for spec_group in specifications:
                if isinstance(spec_group, dict) and 'attributes' in spec_group:
                    attributes = spec_group['attributes']
                    if isinstance(attributes, list):
                        property_count += len(attributes)
            
            # Also check other common property field names as fallback
            property_fields = ['properties', 'attributes', 'specs', 'details']
            
            for field in property_fields:
                if field in product_data and product_data[field]:
                    if isinstance(product_data[field], list):
                        property_count = max(property_count, len(product_data[field]))
                    elif isinstance(product_data[field], dict):
                        property_count = max(property_count, len(product_data[field]))
        
        self.analyzed_products += 1
        self.max_properties = max(self.max_properties, property_count)
        
        return property_count
    
    def analyze_json_file(self, file_path: str) -> int:
        """
        Analyze a JSON file containing product data
        Returns the maximum number of properties found across all products
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Array of products
                for product in data:
                    self.analyze_product_properties(product)
            elif isinstance(data, dict):
                # Check for Digikala API response structure
                if 'data' in data and 'product' in data['data']:
                    # Digikala API response: {data: {product: {...}}}
                    self.analyze_product_properties(data['data']['product'])
                elif 'products' in data:
                    # Nested under 'products' key
                    for product in data['products']:
                        self.analyze_product_properties(product)
                else:
                    # Single product
                    self.analyze_product_properties(data)
            
            logger.info(f"Analyzed {self.analyzed_products} products from {file_path}")
            logger.info(f"Maximum properties found: {self.max_properties}")
            
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
        
        return self.max_properties
    
    def get_max_properties(self) -> int:
        """Get the maximum number of properties found so far"""
        return self.max_properties
    
    def reset(self):
        """Reset the analyzer state"""
        self.max_properties = 0
        self.analyzed_products = 0


def get_max_properties_from_data(data_sources: List[str] = None) -> int:
    """
    Convenience function to get maximum properties from various data sources
    
    Args:
        data_sources: List of file paths to analyze. If None, will try common locations.
    
    Returns:
        Maximum number of properties found
    """
    analyzer = PropertyAnalyzer()
    
    if data_sources is None:
        # Try common data file locations
        data_sources = [
            'products.json',
            'scraped_data.json', 
            'output.json',
            '../products.json',
            '../scraped_data.json',
            '../output.json'
        ]
    
    max_props = 0
    for source in data_sources:
        try:
            current_max = analyzer.analyze_json_file(source)
            max_props = max(max_props, current_max)
        except Exception as e:
            logger.debug(f"Could not analyze {source}: {e}")
            continue
    
    return max_props


def update_product_item_class(max_properties: int = None):
    """
    Update the ProductItem class with the correct number of property fields
    
    Args:
        max_properties: Number of properties to support. If None, will analyze existing data.
    """
    if max_properties is None:
        max_properties = get_max_properties_from_data()
        logger.info(f"Auto-detected maximum properties: {max_properties}")
    
    # Import here to avoid circular imports
    try:
        from .items import create_dynamic_product_item
    except ImportError:
        from items import create_dynamic_product_item
    
    import sys
    
    # Update the ProductItem class in the items module
    items_module = sys.modules.get('digikala_scraper.items') or sys.modules.get('items')
    if items_module:
        items_module.ProductItem = create_dynamic_product_item(max_properties)
        logger.info(f"Updated ProductItem class to support {max_properties} properties")
    
    return max_properties