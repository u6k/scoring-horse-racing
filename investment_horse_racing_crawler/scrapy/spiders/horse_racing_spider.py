import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import scrapy
from scrapy.loader import ItemLoader

from investment_horse_racing_crawler.app_logging import get_logger
from investment_horse_racing_crawler.scrapy.items import RaceInfoItem, RacePayoffItem, RaceResultItem, RaceDenmaItem, HorseItem, TrainerItem, JockeyItem, OddsWinPlaceItem


logger = get_logger(__name__)


class HorseRacingSpider(scrapy.Spider):
    name = "horse_racing"

    def __init__(self, start_url='https://keiba.yahoo.co.jp/schedule/list/', recrawl_period="all", recrawl_race_id=None, recache_race=False, recache_horse=False, *args, **kwargs):
        super(HorseRacingSpider, self).__init__(*args, **kwargs)

        self.start_urls = [start_url]

        if recrawl_period == "all":
            recrawl_period = 100000
        recrawl_period = int(recrawl_period)
        self.recrawl_end_date = datetime(datetime.now().year, datetime.now().month, datetime.now().day, 0, 0, 0, 0) + timedelta(days=1)
        self.recrawl_start_date = self.recrawl_end_date - timedelta(days=recrawl_period)

        self.recrawl_race_id = recrawl_race_id
        self.recache_race = recache_race
        self.recache_horse = recache_horse

    def parse(self, response):
        """ Parse schedule list page.

        @url https://keiba.yahoo.co.jp/schedule/list/2019/?month=12
        @returns items 0 0
        @returns requests 1
        @schedule_list
        """
        logger.info("#parse: start: url=%s" % response.url)

        logger.debug(f"#parse: recrawl_start_date={self.recrawl_start_date}")
        logger.debug(f"#parse: recrawl_end_date={self.recrawl_end_date}")
        logger.debug(f"#parse: recrawl_race_id={self.recrawl_race_id}")
        logger.debug(f"#parse: recache_race={self.recache_race}")
        logger.debug(f"#parse: recache_horse={self.recache_horse}")

        if self.recrawl_race_id:
            logger.debug(f"#parse: re-crawl race: {self.recrawl_race_id}")

            yield response.follow(f"/race/denma/{self.recrawl_race_id}/", callback=self.parse_race_denma)
            yield response.follow(f"/odds/tfw/{self.recrawl_race_id}/", callback=self.parse_odds)
            yield response.follow(f"/race/result/{self.recrawl_race_id}/", callback=self.parse_race_result)

            return

        for a in response.xpath("//a"):
            href = a.xpath("@href").get()

            target_re = re.match("^/schedule/list/([0-9]+)/\\?month=([0-9]+)$", href)
            if target_re:
                logger.debug("#parse: other schedule list page: href=%s" % href)

                # Check re-crawl
                target_start = datetime(int(target_re.group(1)), int(target_re.group(2)), 1, 0, 0, 0)
                target_end = target_start + relativedelta(months=1)

                if not (self.recrawl_start_date <= target_end and self.recrawl_end_date >= target_start):
                    logger.debug(f"#parse: cancel other schedule list page: target={target_start} to {target_end}, settings={self.recrawl_start_date} to {self.recrawl_end_date}")
                    continue

                yield response.follow(a, callback=self.parse)

            if href.startswith("/race/list/"):
                logger.debug("#parse: race list page: href=%s" % href)
                yield response.follow(a, callback=self.parse_race_list)

    def parse_race_list(self, response):
        """ Parse race list page.

        @url https://keiba.yahoo.co.jp/race/list/19060502/
        @returns items 0 0
        @returns requests 1
        @race_list
        """
        logger.info("#parse_race_list: start: url=%s" % response.url)

        # Check re-crawl
        target_date_re = re.match("^([0-9]+)年([0-9]+)月([0-9]+)日.*$", response.xpath("//div[@id='cornerTit']/h4/text()").get())
        if not target_date_re:
            raise RuntimeError("#parse_race_list: target date not found")

        target_date = datetime(int(target_date_re.group(1)), int(target_date_re.group(2)), int(target_date_re.group(3)), 0, 0, 0, 0)
        if not (self.recrawl_start_date <= target_date < self.recrawl_end_date):
            logger.debug(f"#parse_race_list: cancel race list: target={target_date}, settings={self.recrawl_start_date} to {self.recrawl_end_date}")
            return

        for a in response.xpath("//a"):
            race_id_re = re.match("^/race/result/([0-9]+)/$", a.xpath("@href").get())
            if race_id_re:
                race_id = race_id_re.group(1)
                logger.debug(f"#parse_race_list: race result page: race_id={race_id}")

                yield response.follow(f"/race/denma/{race_id}/", callback=self.parse_race_denma)
                yield response.follow(f"/odds/tfw/{race_id}/", callback=self.parse_odds)
                yield response.follow(f"/race/result/{race_id}/", callback=self.parse_race_result)

    def parse_race_result(self, response):
        """ Parse race result page.

        @url https://keiba.yahoo.co.jp/race/result/1906050201/
        @returns items 1
        @returns requests 0 0
        @race_result
        """
        logger.info("#parse_race_result: start: url=%s" % response.url)

        # Parse race payoff
        logger.debug("#parse_race_result: parse race payoff")

        race_id = response.url.split("/")[-2]

        payoff_type = None
        for tr in response.xpath("//table[contains(@class, 'resultYen')]/tr"):
            payoff_type_str = tr.xpath("th/text()").get()
            if payoff_type_str is not None:
                payoff_type = payoff_type_str

            loader = ItemLoader(item=RacePayoffItem(), selector=tr)
            loader.add_value("race_id", race_id)
            loader.add_value("payoff_type", payoff_type)
            loader.add_xpath("horse_number", "td[1]/text()")
            loader.add_xpath("odds", "td[2]/text()")
            loader.add_xpath("favorite_order", "td[3]/span/text()")
            i = loader.load_item()

            logger.debug("#parse_race_result: race payoff=%s" % i)
            yield i

        # Parse race result
        logger.debug("#parse_race_result: parse race result")

        for tr in response.xpath("//table[@id='raceScore']/tbody/tr"):
            loader = ItemLoader(item=RaceResultItem(), selector=tr)
            loader.add_value("race_id", race_id)
            loader.add_xpath("result", "td[1]/text()")
            loader.add_xpath("bracket_number", "td[2]/span/text()")
            loader.add_xpath("horse_number", "td[3]/text()")
            loader.add_xpath("horse_id", "td[4]/a/@href")
            loader.add_xpath("horse_name", "td[4]/a/text()")
            loader.add_xpath("horse_gender_age", "td[4]/span/text()")
            loader.add_xpath("horse_weight_and_diff", "td[4]/span/text()")
            loader.add_xpath("arrival_time", "td[5]/text()[1]")
            loader.add_xpath("jockey_id", "td[7]/a/@href")
            loader.add_xpath("jockey_name", "td[7]/a/text()")
            loader.add_xpath("jockey_weight", "td[7]/span/text()")
            loader.add_xpath("favorite_order", "td[8]/text()[1]")
            loader.add_xpath("odds", "td[8]/span/text()")
            loader.add_xpath("trainer_id", "td[9]/a/@href")
            loader.add_xpath("trainer_name", "td[9]/a/text()")
            i = loader.load_item()

            logger.debug("#parse_race_result: race result=%s" % i)
            yield i

    def parse_race_denma(self, response):
        """ Parse denma page.

        @url https://keiba.yahoo.co.jp/race/denma/1906050201/
        @returns items 1
        @returns requests 1
        @race_denma
        """
        logger.info("#parse_race_denma: start: url=%s" % response.url)

        # Parse race info
        logger.debug("#parse_race_denma: parse race info")

        loader = ItemLoader(item=RaceInfoItem(), response=response)
        race_id = response.url.split("/")[-2]
        loader.add_value("race_id", race_id)
        loader.add_xpath("race_round", "//td[@id='raceNo']/text()")
        loader.add_xpath("start_date", "//p[@id='raceTitDay']/text()[1]")
        loader.add_xpath("start_time", "//p[@id='raceTitDay']/text()[3]")
        loader.add_xpath("place_name", "//p[@id='raceTitDay']/text()[2]")
        loader.add_xpath("race_name", "//div[@id='raceTitName']/h1/text()")
        loader.add_xpath("course_type_length", "//p[@id='raceTitMeta']/text()[1]")
        loader.add_xpath("weather", "//p[@id='raceTitMeta']/img[1]/@alt")
        loader.add_xpath("course_condition", "//p[@id='raceTitMeta']/img[2]/@alt")
        loader.add_xpath("added_money", "//p[@id='raceTitMeta']/text()[8]")
        i = loader.load_item()

        logger.debug("#parse_race_denma: race info=%s" % i)
        yield i

        # Parse race denma
        logger.debug("#parse_race_denma: parse race denma")

        for tr in response.xpath("//table[contains(@class, 'denmaLs')]/tr[position()>1]"):
            loader = ItemLoader(item=RaceDenmaItem(), selector=tr)
            loader.add_value("race_id", race_id)
            loader.add_xpath("bracket_number", "td[1]/span/text()")
            loader.add_xpath("horse_number", "td[2]/strong/text()")
            loader.add_xpath("horse_id", "td[3]/a/@href")
            loader.add_xpath("trainer_id", "td[3]/span/a/@href")
            loader.add_xpath("horse_weight_and_diff", "string(td[4])")
            loader.add_xpath("jockey_id", "td[5]/a/@href")
            loader.add_xpath("jockey_weight", "td[5]/text()")
            loader.add_xpath("prize_total_money", "td[7]/text()[3]")
            i = loader.load_item()

            logger.debug("#parse_race_denma: race denma=%s" % i)
            yield i

        # Parse link
        logger.debug("#parse_race_denma: parse link")

        for a in response.xpath("//a"):
            href = a.xpath("@href").get()

            if href.startswith("/directory/horse/"):
                logger.debug("#parse_race_denma: horse page: href=%s" % href)
                yield response.follow(a, callback=self.parse_horse)

            if href.startswith("/directory/trainer/"):
                logger.debug("#parse_race_denma: trainer page: href=%s" % href)
                yield response.follow(a, callback=self.parse_trainer)

            if href.startswith("/directory/jocky/"):
                logger.debug("#parse_race_denma: jockey page: href=%s" % href)
                yield response.follow(a, callback=self.parse_jockey)

    def parse_horse(self, response):
        """ Parse horse page.

        @url https://keiba.yahoo.co.jp/directory/horse/2017101602/
        @returns items 1 1
        @returns requests 0 0
        @horse
        """
        logger.info("#parse_horse: start: url=%s" % response.url)

        horse_id = response.url.split("/")[-2]

        loader = ItemLoader(item=HorseItem(), response=response)
        loader.add_value("horse_id", horse_id)
        loader.add_xpath("gender", "string(//div[@id='dirTitName']/p)")
        loader.add_xpath("name", "//div[@id='dirTitName']/h1/text()")
        loader.add_xpath("birthday", "//div[@id='dirTitName']/ul/li[1]/text()")
        loader.add_xpath("coat_color", "//div[@id='dirTitName']/ul/li[2]/text()")
        loader.add_xpath("trainer_id", "//div[@id='dirTitName']/ul/li[3]/a/@href")
        loader.add_xpath("owner", "//div[@id='dirTitName']/ul/li[4]/text()")
        loader.add_xpath("breeder", "//div[@id='dirTitName']/ul/li[5]/text()")
        loader.add_xpath("breeding_farm", "//div[@id='dirTitName']/ul/li[6]/text()")
        i = loader.load_item()

        logger.debug("#parse_horse: horse=%s" % i)
        yield i

    def parse_trainer(self, response):
        """ Parse trainer page.

        @url https://keiba.yahoo.co.jp/directory/trainer/01012/
        @returns items 1
        @returns requests 0 0
        @trainer
        """
        logger.info("#parse_trainer: start: url=%s" % response.url)

        trainer_id = response.url.split("/")[-2]

        loader = ItemLoader(item=TrainerItem(), response=response)
        loader.add_value("trainer_id", trainer_id)
        loader.add_xpath("name_kana", "//div[@id='dirTitName']/p/text()[1]")
        loader.add_xpath("name", "//div[@id='dirTitName']/h1/text()")
        loader.add_xpath("birthday", "//div[@id='dirTitName']/ul/li[1]/text()")
        loader.add_xpath("belong_to", "//div[@id='dirTitName']/ul/li[2]/text()")
        loader.add_xpath("first_licensing_year", "//div[@id='dirTitName']/ul/li[3]/text()")
        i = loader.load_item()

        logger.debug("#parse_trainer: trainer=%s" % i)
        yield i

    def parse_jockey(self, response):
        """ Parse jockey page.

        @url https://keiba.yahoo.co.jp/directory/jocky/01167/
        @returns items 1
        @returns requests 0 0
        @jockey
        """
        logger.info("#parse_jockey: start: url=%s" % response.url)

        jockey_id = response.url.split("/")[-2]

        loader = ItemLoader(item=JockeyItem(), response=response)
        loader.add_value("jockey_id", jockey_id)
        loader.add_xpath("name_kana", "//div[@id='dirTitName']/p/text()[1]")
        loader.add_xpath("name", "//div[@id='dirTitName']/h1/text()")
        loader.add_xpath("birthday", "//div[@id='dirTitName']/ul/li[1]/text()")
        loader.add_xpath("belong_to", "//div[@id='dirTitName']/ul/li[2]/text()")
        loader.add_xpath("first_licensing_year", "//div[@id='dirTitName']/ul/li[3]/text()")
        i = loader.load_item()

        logger.debug("#parse_jockey: jockey=%s" % i)
        yield i

    def parse_odds(self, response):
        """ Parse odds page.

        @url https://keiba.yahoo.co.jp/odds/tfw/1906050201/
        @returns items 1
        @returns requests 0 0
        @odds_win_place
        """
        logger.info("#parse_odds: start: url=%s" % response.url)

        race_id = response.url.split("/")[-2]

        for tr in response.xpath("//table[@class='dataLs oddTkwLs']/tbody/tr"):
            if len(tr.xpath("th")) > 0:
                continue

            loader = ItemLoader(item=OddsWinPlaceItem(), selector=tr)
            loader.add_value("race_id", race_id)
            loader.add_xpath("horse_number", "td[2]/text()")
            loader.add_xpath("horse_id", "td[3]/a/@href")
            loader.add_xpath("odds_win", "td[4]/text()")
            loader.add_xpath("odds_place_min", "td[5]/text()")
            loader.add_xpath("odds_place_max", "td[7]/text()")

            i = loader.load_item()

            logger.debug("#parse_odds: odds=%s" % i)
            yield i
