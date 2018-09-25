"""Scraping damart products."""
import json
import re
import time
import scrapy
from damart_code.items import DamartCodeItem


class DaMartSpider(scrapy.Spider):
    """Spider."""
    name = 'damart'
    start_time = time.time()
    start_urls = ['https://www.damart.co.uk/home']
    header = {'X-Requested-With': 'XMLHttpRequest'}
    end_time = time.time()

    def parse(self, response):
        """Extracts links from homepage."""
        if response.status != 200:
            return
        sections = response.xpath('//nav[@id="navbar"]/ul//a/@href').extract()
        for section in sections:
            section = section + '/I-Page1_2000'
            yield response.follow(section, callback=self.parse_sections)

    def parse_sections(self, response):
        """If yielded pages have further sections it extract there links."""
        if response.status != 200:
            return

        categories = response.xpath('//div[@id="bannerLinks"]/div/a/@href').extract()
        if not categories:
            categories = response.xpath('//div[@class="CTAs"]/a/@href').extract()

        if not categories:
            categories = response.xpath('//div[@class="RCthreePanelsActivity"]/a/@href').extract()

        if not categories:
            categories = response.xpath('//div[@class="CTAs"]/div/a/@href').extract()

        for category in categories:
            yield response.follow(category + '/I-Page1_2000', callback=self.parse_collection)
        req = response.follow(response.url, callback=self.parse_collection)
        yield req

    def parse_collection(self, response):
        """Redirect to each product page."""
        if response.status != 200:
            return
        collection = response.xpath('//div[@class="k-product"]/a[@class="name"]/@href').extract()
        for item in collection:
            yield response.follow(item, callback=self.parse_product)

    def parse_size(self, response):
        """Fetch available sizes for different colors and lengths if product has that attribute"""
        #raw_variants = [ color , json url]
        if response.status != 200:
            return

        json_response = json.loads(response.body_as_unicode())

        available_lengths = []
        if len(json_response['inits'][2]['initDDdSlickComponent']) > 1:
            length_data = json_response['inits'][2]['initDDdSlickComponent'][1].get('ddData')
            for trouser_length in length_data:
                available_lengths += [trouser_length['text']]

        raw_variants = response.meta['raw_variants']
        variants = response.meta['variants']
        if raw_variants:
            color = raw_variants[0][0]
            del raw_variants[0]
            available_sizes = []
            for iterator in range(len(json_response['inits'][2]['initDDdSlickComponent'][0]
                                      ['ddData'])):
                availability = json_response['inits'][2]['initDDdSlickComponent'][0] \
                    ['ddData'][iterator].get('description')
                if availability is not None and \
                        re.findall(r'>[\w]+<', availability) == ['>Available<']:
                    available_sizes = available_sizes + [json_response['inits'][2]
                                                         ['initDDdSlickComponent'][0]
                                                         ['ddData'][iterator]['text']]
                elif availability is None:
                    available_sizes = available_sizes + [json_response['inits'][2]
                                                         ['initDDdSlickComponent'][0]
                                                         ['ddData'][iterator]['text']]
            variants = variants + [{'Color': color, 'Available Sizes': available_sizes}]
            if raw_variants:
                yield response.follow(raw_variants[0][1], callback=self.parse_size,
                                      headers=self.header,
                                      meta={'details': response.meta['details'],
                                            'raw_variants': raw_variants, 'variants': variants})
            else:
                product_details = response.meta['details']
                product_details['variants'] = variants
                if available_lengths:
                    product_details['available_lenghts'] = available_lengths
                yield product_details

    def parse_product(self, response):
        """Fetch html based product details."""
        if response.status != 200:
            return

        pricing = response.xpath('//div[@itemprop="offers"]')
        if pricing.xpath('p[contains(@class,"no_promo")]/text()').extract_first() is not None:
            pricing = {'Actual Price': pricing.xpath('p[contains(@class,"no_promo")]/text()') \
                                           .extract_first() +
                                       pricing.xpath('p[contains(@class,"no_promo")]/span/text()') \
                                           .extract_first(), 'Sale Price': 0.00}

        else:
            pricing = {'Actual Price': pricing.xpath('//span[@itemprop="price"]/text()') \
                                           .extract_first() +
                                       pricing.xpath('//span[@itemprop="price"]/span/text()') \
                                           .extract_first(),
                       'Sale Price': pricing.xpath('//p[contains(@class,"sale")]/text()') \
                                         .extract_first() +
                                     pricing.xpath('//p[contains(@class,"sale")]//span/text()') \
                                         .extract_first()}

        description = response.xpath('//div[contains(@class,"new_info-desc")]/p/strong/text()') \
                          .extract() + \
                      response.xpath('//div[contains(@class,"new_info-desc")]/ul/li/text()') \
                          .extract() + \
                      response.xpath('//div[contains(@class,"new_info-desc")]'
                                     '/p[@id="description-block"]/text()').extract()

        colors = response.xpath('//ul[@class="picto_color"]/li/a/@title').extract()
        sizes = response.xpath('//ul[@class="picto_color"]/li/a/@href').extract()

        raw_variants = []
        for iterator, _ in enumerate(colors):
            raw_variants += [[colors[iterator], sizes[iterator]]]

        hirierchy = response.xpath('//div[@class="breadcrum"]//span[@itemprop="title"]/text()') \
            .extract()

        images = response.xpath('//ul[contains(@class,"thumblist")]/li/a/@href').extract()
        images = [refine_img[2:] for refine_img in images]

        item = DamartCodeItem()
        item["product_id"] = response.xpath('//span[@itemprop="productID"]/text()').extract_first()
        item["name"] = hirierchy[-1]
        item["section"] = hirierchy[-3]
        item["collection"] = hirierchy[-2]
        item["pricing"] = pricing
        item["weblink"] = response.url
        item["description"] = description
        item["images"] = images
        if raw_variants:
            yield response.follow(response.xpath('//ul[@class="picto_color"]/li/a/@href')
                                  .extract_first(),
                                  headers=self.header, callback=self.parse_size,
                                  meta={'details': item, 'raw_variants': raw_variants,
                                        'variants': []})
        else:
            yield item
