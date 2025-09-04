import csv
import json
import os
import re
import requests
import scrapy
from urllib.parse import urlparse
from digikala_scraper.items import ProductItem, create_dynamic_product_item
from digikala_scraper.property_analyzer import PropertyAnalyzer


class ProductDetailsSpider(scrapy.Spider):
    name = "digikalaProduct"
    
    def __init__(self, *args, **kwargs):
        super(ProductDetailsSpider, self).__init__(*args, **kwargs)
        self.setup_dynamic_items()
        # Default images directory, will be updated in from_crawler
        self.images_dir = 'images'
        self.create_images_directory()
        # Load SKU prefix from sku.txt
        self.sku_prefix = self.load_sku_prefix()
        self.variation_counter = 1
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        # Now settings are available, update images directory
        spider.images_dir = crawler.settings.get('IMAGES_DIRECTORY', 'images')
        spider.create_images_directory()  # Recreate with correct directory
        return spider
    
    def setup_dynamic_items(self):
        """Setup dynamic ProductItem class based on configuration or analysis"""
        config_file = 'dynamic_items_config.json'
        
        if os.path.exists(config_file):
            # Load from configuration file
            with open(config_file, 'r') as f:
                config = json.load(f)
            max_properties = config.get('max_properties', 0)
            self.logger.info(f"Loaded configuration: max_properties = {max_properties}")
        else:
            # Use a generous default - the pipeline will expand as needed
            max_properties = 50
            self.logger.info("No configuration found, using default 50 properties")
        
        # Create dynamic ProductItem class and store it as instance variable
        self.DynamicProductItem = create_dynamic_product_item(max_properties)
        self.max_properties = max_properties
        self.logger.info(f"ProductItem configured for {max_properties} properties (pipeline will expand if needed)")
    
    # def analyze_sample_product(self):
    #     """Analyze a sample product to determine property count"""
    #     try:
    #         import requests
    #         response = requests.get("http://api.digikala.com/v2/product/9674032/", timeout=10)
    #         if response.status_code == 200:
    #             data = response.json()
    #             product_data = data.get("data", {}).get("product", {})
                
    #             analyzer = PropertyAnalyzer()
    #             max_properties = analyzer.analyze_product_properties(product_data)
    #             self.logger.info(f"Analyzed sample product: {max_properties} properties found")
    #             return max_properties
    #     except Exception as e:
    #         self.logger.warning(f"Could not analyze sample product: {e}")
        
    #     return 30  # fallback default - increased based on your example
    
    def create_images_directory(self):
        """Create images directory if it doesn't exist"""
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
            self.logger.info(f"Created images directory: {self.images_dir}")
    
    def load_sku_prefix(self):
        """Load SKU prefix from sku.txt file"""
        try:
            with open('sku.txt', 'r', encoding='utf-8') as f:
                prefix = f.read().strip()
                self.logger.info(f"Loaded SKU prefix: {prefix}")
                return prefix
        except Exception as e:
            self.logger.error(f"Error loading sku.txt: {e}")
            return "default"
    
    
    def download_image(self, url, filename):
        """Download image from URL and save to images directory"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            filepath = os.path.join(self.images_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to download image {url}: {e}")
            return None
    
    def extract_and_download_images(self, product_data, sku):
        """Extract image URLs and download up to 4 images (main + 3 from list) using SKU-based naming"""
        images_data = product_data.get("images", {})
        downloaded_images = []
        
        # Download main image first
        main_images = images_data.get("main", {})
        main_urls = main_images.get("url", [])
        if main_urls:
            main_url = main_urls[0]
            # Extract file extension from URL
            parsed_url = urlparse(main_url)
            ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
            filename = f"{sku}-1{ext}"
            
            filepath = self.download_image(main_url, filename)
            if filepath:
                downloaded_images.append(filepath)
        
        # Download up to 3 additional images from list
        image_list = images_data.get("list", [])
        for i, image_item in enumerate(image_list[:3]):  # Limit to 3 additional images
            urls = image_item.get("url", [])
            if urls:
                url = urls[0]
                parsed_url = urlparse(url)
                ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
                filename = f"{sku}-{i+2}{ext}"  # Start from 2 since main image is 1
                
                filepath = self.download_image(url, filename)
                if filepath:
                    downloaded_images.append(filepath)
        
        # Return comma-separated list of filepaths
        return ",".join(downloaded_images)
    
    def start_requests(self):
        with open("urls.csv", "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                url = row["url"]
                title = row["title_fa"]
                
                product_id = self.extract_product_id(url)
                if product_id:
                    api_url = f"http://api.digikala.com/v2/product/{product_id}/"
                    yield scrapy.Request(
                        url=api_url, 
                        callback=self.parse_product,
                        meta={'title': title, 'product_id': product_id}
                    )
    
    def extract_product_id(self, url):
        match = re.search(r'dkp-(\d+)', url)
        return match.group(1) if match else None
    
    def parse_product(self, response):
        jsonresponse = response.json()
        product_data = jsonresponse.get("data", {}).get("product", {})
        
        # Check if product has colors
        colors = product_data.get("colors", [])
        base_uuid = str(jsonresponse["data"]["product"]["id"])
        base_sku = f"{self.sku_prefix}-{base_uuid}"
        
        if len(colors) > 1:
            # Reset variation counter for each product
            self.variation_counter = 1
            # Create variable product (parent)
            yield from self.create_variable_product(product_data, base_sku, colors, jsonresponse)
            
            # Create variation products for each color
            for color in colors:
                yield from self.create_variation_product(product_data, base_sku, color, jsonresponse)
        else:
            # Create simple product
            yield from self.create_simple_product(product_data, base_sku, jsonresponse)
    
    def create_simple_product(self, product_data, sku, jsonresponse):
        """Create a simple product"""
        product = self.DynamicProductItem()
        
        # Basic fields - match exact field names from items.py
        product["شناسه"] = ""
        product["SKU"] = sku
        product["نوع"] = "simple"
        product["نام"] = product_data.get("title_fa", "")
        product["منتشر شده"] = "1" if product_data.get("status") == "marketable" else "0"
        
        # Fill product data
        colors = product_data.get("colors", [])
        self.fill_product_data(product, product_data, jsonresponse, colors=colors)
        yield product
    
    def create_variable_product(self, product_data, base_sku, colors, jsonresponse):
        """Create a variable product (parent)"""
        product = self.DynamicProductItem()
        
        # Basic fields
        product["شناسه"] = ""
        product["SKU"] = base_sku
        product["نوع"] = "variable"
        product["نام"] = product_data.get("title_fa", "")
        product["منتشر شده"] = "1" if product_data.get("status") == "marketable" else "0"
        product["مادر"] = ""
        
        # Fill product data
        self.fill_product_data(product, product_data, jsonresponse, colors=colors)
        yield product
    
    def create_variation_product(self, product_data, base_sku, color, jsonresponse):
        """Create a variation product for a specific color"""
        product = self.DynamicProductItem()
        
        # Basic fields
        color_name = color.get("title", "")
        variation_sku = f"{base_sku}-{self.variation_counter}"
        self.variation_counter += 1
        
        product["شناسه"] = ""
        product["SKU"] = variation_sku
        product["نوع"] = "variation"
        product["نام"] = f"{product_data.get('title_fa', '')} - {color_name}"
        product["منتشر شده"] = "1" if product_data.get("status") == "marketable" else "0"
        product["مادر"] = base_sku
        
        # Fill product data
        self.fill_product_data(product, product_data, jsonresponse, color_name)
        yield product
    
    def fill_product_data(self, product, product_data, jsonresponse, color_name=None, colors=None):
        """Fill common product data"""
        
        # Get colors to determine if we need to add color as property
        colors = product_data.get("colors", [])
        # Check if product has special pricing
        price_data = product_data.get("price", {})
        is_special = "1" if price_data.get("discount_percent", 0) > 0 else "0"
        product["آیا ویژه است؟"] = is_special
        
        product["قابل مشاهده در کاتالوگ"] = "visible"
        product["توضیح کوتاه"] = product_data.get("review", {}).get("description", "")[:500] + "..." if len(product_data.get("review", {}).get("description", "")) > 500 else product_data.get("review", {}).get("description", "")
        product["توضیحات"] = product_data.get("review", {}).get("description", "")
        product["تاریخ شروع فروش ویژه"] = ""
        product["تاریخ پایان فروش ویژه"] = ""
        product["وضعیت مالیات"] = "taxable"
        product["کلاس مالیاتی"] = "standard"
        
        # Stock information
        default_variant = product_data.get("default_variant", {})
        if isinstance(default_variant, dict):
            stock_info = default_variant.get("price", {})
            stock_count = stock_info.get("marketable_stock", 0)
        else:
            stock_count = 0
        product["در انبار؟"] = "1" if stock_count > 0 else "0"
        product["انبار"] = str(stock_count)
        product["کمبود موجودی انبار"] = "1" if stock_count < 5 else "0"
        
        product["پیش‌فروش مجاز است؟"] = "0"
        product["فروش به صورت جداگانه؟"] = "1"
        
        # Try to get product dimensions if available
        product["وزن"] = ""
        product["درازا"] = ""
        product["پهنا"] = ""
        product["بلندا"] = ""
        product["یادداشت خرید"] = ""
        
        # Categories
        intrack_data = jsonresponse.get("data", {}).get("intrack", {}).get("eventData", {})
        categories = []
        for i in range(1, 6):
            cat = intrack_data.get(f"categoryLevel{i}", "")
            if cat:
                categories.append(cat)
        product["دسته‌ها"] = " > ".join(categories)
        
        product["برچسب‌ها"] = ""
        product["کلاس حمل و نقل"] = ""
        product["محدودیت دانلود"] = ""
        product["روز انقضاء دانلود"] = ""
        product["محصولات گروهی"] = ""
        product["تشویق برای خرید بیشتر"] = ""
        product["محصولات مشابه"] = ""
        product["آدرس خارجی"] = ""
        product["متن دکمه"] = ""
        product["موقعیت"] = ""
        product["برندها"] = product_data.get("brand", {}).get("title_fa", "")
        
        # Download and save images (only for non-variation products)
        if color_name is None:  # Only download images for simple and variable products, not variations
            images_paths = self.extract_and_download_images(product_data, product["SKU"])
            product["تصاویر"] = images_paths
        else:
            product["تصاویر"] = ""  # Variations don't have images

        # Get pricing from default variant
        if isinstance(default_variant, dict):
            variant_price = default_variant.get("price", {})
            regular_price = variant_price.get("rrp_price", variant_price.get("selling_price", ""))
            selling_price = variant_price.get("selling_price", "")
        else:
            regular_price = ""
            selling_price = ""
        
        product["قیمت عادی"] = str(regular_price) if regular_price else ""
        product["قیمت فروش ویژه"] = str(selling_price) if selling_price else ""

        # Handle dynamic properties from specifications
        specifications = product_data.get("specifications", [])
        property_index = 1
        
        # Add color as property
        product_colors = colors if colors is not None else product_data.get("colors", [])
        
        if color_name:
            # For variations, use the specific color
            product[f"نام {property_index} صفت"] = "رنگ"
            product[f"مقدار {property_index} صفت"] = color_name
            product[f"نمایان بودن {property_index} صفت"] = "1"
            property_index += 1
        elif product_colors:
            # For simple and variable products, add color(s)
            if len(product_colors) == 1:
                # Single color for simple products
                color = product_colors[0]
                product[f"نام {property_index} صفت"] = "رنگ"
                product[f"مقدار {property_index} صفت"] = color.get("title", "")
                product[f"نمایان بودن {property_index} صفت"] = "1"
                property_index += 1
            else:
                # Multiple colors for variable products - comma separated
                color_names = [color.get("title", "") for color in product_colors]
                product[f"نام {property_index} صفت"] = "رنگ"
                product[f"مقدار {property_index} صفت"] = ",".join(color_names)
                product[f"نمایان بودن {property_index} صفت"] = "1"
                property_index += 1
        
        for spec_group in specifications:
            if isinstance(spec_group, dict) and 'attributes' in spec_group:
                for attribute in spec_group['attributes']:
                    # Check if we need to expand the ProductItem dynamically
                    if property_index > self.max_properties:
                        self.logger.warning(f"Product {product_data.get('id')} has {property_index} properties, but ProductItem only supports {self.max_properties}. Expanding dynamically...")
                        # Recreate ProductItem with more fields
                        new_max = property_index + 10  # Add some buffer
                        self.DynamicProductItem = create_dynamic_product_item(new_max)
                        self.max_properties = new_max
                        
                        # Recreate the product item with the new class
                        old_data = {}
                        # Only copy fields that have been set
                        for key in product.fields:
                            if key in product:
                                old_data[key] = product[key]
                        
                        product = self.DynamicProductItem()
                        # Copy existing data
                        for key, value in old_data.items():
                            product[key] = value
                    
                    # Now safely add the property
                    product[f"نام {property_index} صفت"] = attribute.get("title", "")
                    product[f"مقدار {property_index} صفت"] = str(attribute.get("values", []))
                    product[f"نمایان بودن {property_index} صفت"] = "1" 
                    property_index += 1

        return product
        