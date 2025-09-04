# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import csv
import os
from scrapy.exporters import CsvItemExporter
from itemadapter import ItemAdapter


class DynamicCSVPipeline:
    """
    Pipeline that dynamically expands CSV columns as new properties are discovered
    """
    
    def __init__(self, csv_file='details.csv'):
        self.csv_file = csv_file
        self.max_properties = 0
        self.fieldnames = []
        self.items_buffer = []
        self.csv_exists = False
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            csv_file=crawler.settings.get('CSV_FILE', 'details.csv')
        )
    
    def open_spider(self, spider):
        """Initialize the pipeline"""
        self.spider = spider
        
        # Check if CSV already exists and get existing column count
        if os.path.exists(self.csv_file):
            self.csv_exists = True
            self._analyze_existing_csv()
        else:
            self._initialize_fieldnames()
    
    def _analyze_existing_csv(self):
        """Analyze existing CSV to determine current max properties"""
        try:
            with open(self.csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                
                # Count existing property columns
                property_count = 0
                for header in headers:
                    if 'صفت' in header and header.endswith('صفت'):
                        # Extract property number from field name like "نام 5 صفت"
                        try:
                            parts = header.split(' ')
                            if len(parts) >= 3 and parts[-1] == 'صفت':
                                prop_num = int(parts[-2])  # Second to last part should be the number
                                property_count = max(property_count, prop_num)
                        except (ValueError, IndexError):
                            continue
                
                self.max_properties = property_count
                self.fieldnames = headers.copy()
                self.spider.logger.info(f"Existing CSV found with {property_count} properties")
                
        except Exception as e:
            self.spider.logger.error(f"Error analyzing existing CSV: {e}")
            self._initialize_fieldnames()
    
    def _initialize_fieldnames(self):
        """Initialize base fieldnames"""
        self.fieldnames = [
            'شناسه', 'SKU', 'نوع', 'نام', 'منتشر شده', 'آیا ویژه است؟',
            'قابل مشاهده در کاتالوگ', 'توضیح کوتاه', 'توضیحات',
            'تاریخ شروع فروش ویژه', 'تاریخ پایان فروش ویژه',
            'وضعیت مالیات', 'کلاس مالیاتی', 'در انبار؟', 'انبار',
            'کمبود موجودی انبار', 'پیش‌فروش مجاز است؟', 'فروش به صورت جداگانه؟',
            'وزن', 'درازا', 'پهنا', 'بلندا', 'یادداشت خرید',
            'قیمت فروش ویژه', 'قیمت عادی', 'دسته‌ها', 'برچسب‌ها',
            'کلاس حمل و نقل', 'تصاویر', 'محدودیت دانلود', 'روز انقضاء دانلود',
            'محصولات گروهی', 'تشویق برای خرید بیشتر', 'محصولات مشابه',
            'آدرس خارجی', 'متن دکمه', 'موقعیت', 'برندها', 'مادر'
        ]
    
    def process_item(self, item, spider):
        """Process each item and check if we need to expand columns"""
        # Only process product details, not URLs
        if spider.name != "product":
            return item
        # Count properties in this item - only check fields that are actually set
        item_properties = 0
        for field_name in item.fields:
            if field_name in item and 'صفت' in field_name and field_name.endswith('صفت'):
                try:
                    # Handle new format: "نام 1 صفت" instead of "نام_1_صفت"
                    parts = field_name.split(' ')
                    if len(parts) >= 3 and parts[-1] == 'صفت':
                        prop_num = int(parts[-2])  # Second to last part should be the number
                        item_properties = max(item_properties, prop_num)
                except (ValueError, IndexError):
                    continue
        
        # If this item has more properties than we've seen before
        if item_properties > self.max_properties:
            spider.logger.info(f"Expanding CSV from {self.max_properties} to {item_properties} properties")
            self._expand_fieldnames(item_properties)
            self.max_properties = item_properties
        
        # Add item to buffer - only include fields that are actually set
        item_dict = {}
        for field_name in item.fields:
            if field_name in item:
                item_dict[field_name] = item[field_name]
        self.items_buffer.append(item_dict)
        
        return item
    
    def _expand_fieldnames(self, new_max_properties):
        """Expand fieldnames to include new property columns"""
        # Remove old property columns
        base_fields = [f for f in self.fieldnames if 'صفت' not in f or not f.endswith('صفت')]
        
        # Add new property columns in correct order
        new_fields = base_fields.copy()
        for i in range(1, new_max_properties + 1):
            new_fields.extend([
                f'نام {i} صفت',
                f'مقدار {i} صفت', 
                f'نمایان بودن {i} صفت'
            ])
        
        self.fieldnames = new_fields
    
    def close_spider(self, spider):
        """Write all buffered items to CSV with final column structure"""
        if not self.items_buffer:
            return
        
        spider.logger.info(f"Writing {len(self.items_buffer)} items to CSV with {self.max_properties} properties")
        
        # Write CSV with all collected data
        with open(self.csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for item_data in self.items_buffer:
                # Fill missing fields with empty strings
                row_data = {}
                for field in self.fieldnames:
                    row_data[field] = item_data.get(field, '')
                writer.writerow(row_data)
        
        spider.logger.info(f"CSV export complete: {self.csv_file}")


class URLCSVPipeline:
    """
    Pipeline for saving URLs to CSV file
    """
    
    def __init__(self, csv_file='urls.csv'):
        self.csv_file = csv_file
        self.file = None
        self.writer = None
        self.headers_written = False
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls()
    
    def open_spider(self, spider):
        """Open CSV file and prepare writer"""
        if spider.name == "digikalaProductUrl":
            self.file = open(self.csv_file, 'w', newline='', encoding='utf-8-sig')
            self.writer = csv.writer(self.file)
    
    def process_item(self, item, spider):
        """Process URL items for digikalaProductUrl spider"""
        if spider.name == "digikalaProductUrl":
            if not self.headers_written:
                # Write headers based on item fields
                headers = list(item.fields.keys())
                self.writer.writerow(headers)
                self.headers_written = True
            
            # Write item data
            row = []
            for field in item.fields.keys():
                row.append(item.get(field, ''))
            self.writer.writerow(row)
            
        return item
    
    def close_spider(self, spider):
        """Close CSV file"""
        if self.file:
            self.file.close()


class DigikalaScraperPipeline:
    def process_item(self, item, spider):
        return item
