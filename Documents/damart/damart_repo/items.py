"""Damart items."""
# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class DamartCodeItem(scrapy.Item):
    """Contains features of damart items."""
    product_id = scrapy.Field()
    name = scrapy.Field()
    section = scrapy.Field()
    collection = scrapy.Field()
    pricing = scrapy.Field()
    weblink = scrapy.Field()
    description = scrapy.Field()
    images = scrapy.Field()
    variants = scrapy.Field()
    available_lenghts = scrapy.Field()
