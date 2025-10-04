import scrapy


def create_dynamic_product_item(max_properties=0):
    """
    Dynamically create ProductItem class with the appropriate number of property fields
    Ensures property fields are grouped together in CSV output
    """
    from collections import OrderedDict
    
    # Use OrderedDict to maintain field order
    class_dict = OrderedDict([
        ('شناسه', scrapy.Field()),
        ('SKU', scrapy.Field()),
        ('نوع', scrapy.Field()),
        ('نام', scrapy.Field()),
        ('منتشر شده', scrapy.Field()),
        ('آیا ویژه است؟', scrapy.Field()),
        ('قابل مشاهده در کاتالوگ', scrapy.Field()),
        ('توضیح کوتاه', scrapy.Field()),
        ('توضیحات', scrapy.Field()),
        ('تاریخ شروع فروش ویژه', scrapy.Field()),
        ('تاریخ پایان فروش ویژه', scrapy.Field()),
        ('وضعیت مالیات', scrapy.Field()),
        ('کلاس مالیاتی', scrapy.Field()),
        ('در انبار؟', scrapy.Field()),
        ('انبار', scrapy.Field()),
        ('کمبود موجودی انبار', scrapy.Field()),
        ('پیش‌فروش مجاز است؟', scrapy.Field()),
        ('فروش به صورت جداگانه؟', scrapy.Field()),
        ('وزن', scrapy.Field()),
        ('درازا', scrapy.Field()),
        ('پهنا', scrapy.Field()),
        ('بلندا', scrapy.Field()),
        ('یادداشت خرید', scrapy.Field()),
        ('قیمت فروش ویژه', scrapy.Field()),
        ('قیمت عادی', scrapy.Field()),
        ('دسته‌ها', scrapy.Field()),
        ('برچسب‌ها', scrapy.Field()),
        ('کلاس حمل و نقل', scrapy.Field()),
        ('تصاویر', scrapy.Field()),
        ('محدودیت دانلود', scrapy.Field()),
        ('روز انقضاء دانلود', scrapy.Field()),
        ('محصولات گروهی', scrapy.Field()),
        ('تشویق برای خرید بیشتر', scrapy.Field()),
        ('محصولات مشابه', scrapy.Field()),
        ('آدرس خارجی', scrapy.Field()),
        ('متن دکمه', scrapy.Field()),
        ('موقعیت', scrapy.Field()),
        ('برندها', scrapy.Field()),
        ('مادر', scrapy.Field()),
        
    ])
    
    # Add dynamic property fields - grouped by property number for proper CSV column ordering
    for i in range(1, max_properties + 1):
        class_dict[f'Attribute {i} name'] = scrapy.Field()
        class_dict[f'Attribute {i} value(s)'] = scrapy.Field()
        class_dict[f'Attribute {i} visible'] = scrapy.Field()
    
    # Create custom Item class that preserves field order
    class OrderedProductItem(scrapy.Item):
        def keys(self):
            # Return keys in the order they were defined
            return list(class_dict.keys())
        
        def __iter__(self):
            # Iterate in the defined order
            return iter(class_dict.keys())
    
    # Add all fields to the class - need to set them as class attributes, not instance
    OrderedProductItem.fields = class_dict.copy()
    for field_name, field_obj in class_dict.items():
        setattr(OrderedProductItem, field_name, field_obj)
    
    return OrderedProductItem
# Default ProductItem with no dynamic properties (will be replaced by create_dynamic_product_item)
ProductItem = create_dynamic_product_item(0)



class Urls(scrapy.Item):
    url = scrapy.Field()
    title_fa = scrapy.Field()