import os
import re
import requests
import scrapy
import logging
import datetime
import urllib.parse
from digikala_scraper.items import *
from scrapy.exceptions import DontCloseSpider

class ProductsSpider(scrapy.Spider):
    name = "url"

    def start_requests(self):
        with open("category_url.txt", mode="r", encoding="utf-8-sig") as f:
            main_url = f.read()
        decoded_url = urllib.parse.unquote(main_url)
        category = None
        brand = None

        if "category" in main_url:
            cat_match = re.search(r'/search/category-([^/?]+)/?', decoded_url)
            brand_match = re.search(r'brands\[\d+\]=(\d+)', decoded_url)

            category = cat_match.group(1) if cat_match else None
            brand = brand_match.group(1) if brand_match else None

            cat_url = f"https://api.digikala.com/v1/categories/{category}/search/?page="
            if brand:
                cat_url = f"https://api.digikala.com/v1/categories/{category}/search/?brands%5B0%5D={brand}&page="       

        elif "brand" in main_url and "category" not in main_url:
            match = re.search(r"/brand/([^/]+)/?", main_url)
            if match:
                brand = match.group(1)
            cat_url = f"https://api.digikala.com/v1/brands/{brand}/?page="

        full_url = f"{cat_url}1"
        
        yield scrapy.Request(url=full_url, callback=self.parse, meta={'page_number': 1, 'base_url': cat_url})

    def parse(self, response):
        page_number = response.meta.get('page_number')
        base_url = response.meta.get('base_url')
        print(page_number)
        
        jsonresponse = response.json()
        products = jsonresponse.get("data", {}).get("products", [])
        if not products:
            return
        
        for product in products:
            product_id = product.get("id")
            product_title = product.get("title_fa")
            if product_id and product_title:
                product_url = f"https://digikala.com/product/dkp-{product_id}/"
                
                url_item = Urls()
                url_item["title_fa"] = product_title
                url_item["url"] = product_url
                yield url_item
        
        next_page = page_number + 1
        if next_page <= 100:
            next_url = f"{base_url}{next_page}"
            yield scrapy.Request(url=next_url, callback=self.parse, meta={'page_number': next_page, 'base_url': base_url})

    # def parse_product(self, response):
    #     jsonresponse = response.json()
        
    #     product = ProductItem()
    #     product["uuid"] = jsonresponse["data"]["product"]["id"]
    #     product["dbid"] = f"digikala-{product['uuid']}"
    #     product["title_fa"] = jsonresponse["data"]["product"]["title_fa"]
    #     product["title_en"] = jsonresponse["data"]["product"]["title_en"]
    #     product["supply_category"] = jsonresponse["data"]["intrack"]["eventData"]["supplyCategory"]
    #     product["category1"] = jsonresponse["data"]["intrack"]["eventData"]["categoryLevel1"]
    #     product["category2"] = jsonresponse["data"]["intrack"]["eventData"]["categoryLevel2"]
    #     product["category3"] = jsonresponse["data"]["intrack"]["eventData"]["categoryLevel3"]
    #     product["category4"] = jsonresponse["data"]["intrack"]["eventData"]["categoryLevel4"]
    #     product["category5"] = jsonresponse["data"]["intrack"]["eventData"]["categoryLevel5"]
        
    #     yield product