#!/usr/bin/env python3
"""
Setup script to configure dynamic ProductItem class based on actual product data
"""
import argparse
import logging
import sys
import os
import json
from property_analyzer import PropertyAnalyzer, update_product_item_class

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_sample_data(api_sample_url="http://api.digikala.com/v2/product/9674032/"):
    """
    Analyze a sample product from the API to understand property structure
    """
    import requests
    
    try:
        response = requests.get(api_sample_url)
        if response.status_code == 200:
            data = response.json()
            product_data = data.get("data", {}).get("product", {})
            
            # Use the PropertyAnalyzer to count properties correctly
            analyzer = PropertyAnalyzer()
            max_properties = analyzer.analyze_product_properties(product_data)
            
            logger.info(f"Maximum properties detected from sample: {max_properties}")
            
            # Log details for debugging
            specifications = product_data.get("specifications", [])
            for i, spec_group in enumerate(specifications):
                if isinstance(spec_group, dict) and 'attributes' in spec_group:
                    attrs = spec_group['attributes']
                    logger.info(f"Specification group {i+1}: {spec_group.get('title', 'Unknown')} - {len(attrs)} attributes")
            
            return max_properties
            
    except Exception as e:
        logger.error(f"Error analyzing sample data: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description='Setup dynamic ProductItem class')
    parser.add_argument('--max-properties', type=int, help='Maximum number of properties to support')
    parser.add_argument('--analyze-sample', action='store_true', help='Analyze sample product from API')
    parser.add_argument('--data-file', type=str, help='JSON file to analyze for properties')
    
    args = parser.parse_args()
    
    max_properties = 0
    
    if args.max_properties:
        max_properties = args.max_properties
        logger.info(f"Using specified max properties: {max_properties}")
        
    elif args.analyze_sample:
        max_properties = analyze_sample_data()
        
    elif args.data_file:
        if os.path.exists(args.data_file):
            analyzer = PropertyAnalyzer()
            max_properties = analyzer.analyze_json_file(args.data_file)
        else:
            logger.error(f"Data file not found: {args.data_file}")
            sys.exit(1)
    else:
        # Default: analyze sample from API
        logger.info("No specific option provided, analyzing sample from API...")
        max_properties = analyze_sample_data()
    
    if max_properties > 0:
        # Update the ProductItem class
        update_product_item_class(max_properties)
        logger.info(f"ProductItem class configured for {max_properties} properties")
        
        # Write config file for the spider to use
        config = {
            'max_properties': max_properties,
            'generated_at': str(datetime.now())
        }
        
        with open('dynamic_items_config.json', 'w') as f:
            json.dump(config, f, indent=2)
            
        logger.info("Configuration saved to dynamic_items_config.json")
    else:
        logger.warning("Could not determine maximum properties. Using default (0)")


if __name__ == "__main__":
    from datetime import datetime
    main()