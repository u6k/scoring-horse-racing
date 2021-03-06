# -*- coding: utf-8 -*-


from scrapy.contracts import Contract
from scrapy.exceptions import ContractFail
from scrapy.http import Request

from investment_horse_racing_crawler.app_logging import get_logger
from investment_horse_racing_crawler.scrapy.items import RaceInfoItem, RacePayoffItem, RaceResultItem, RaceDenmaItem, HorseItem, TrainerItem, JockeyItem, OddsWinPlaceItem


logger = get_logger(__name__)


class ScheduleListContract(Contract):
    name = "schedule_list"

    def post_process(self, output):
        logger.debug("ScheduleListContract#post_process: start")

        requests = [o for o in output if isinstance(o, Request)]
        if len(requests) < 1:
            raise ContractFail("Empty requests")

        for request in requests:
            if request.url.startswith("https://keiba.yahoo.co.jp/schedule/list/"):
                continue

            if request.url.startswith("https://keiba.yahoo.co.jp/race/list/"):
                continue

            raise ContractFail("Unknown request url: url=%s" % request.url)


class RaceListContract(Contract):
    name = "race_list"

    def post_process(self, output):
        logger.debug("RaceListContract#post_process: start")

        requests = [o for o in output if isinstance(o, Request)]

        race_denma_count = 0
        for request in requests:
            if request.url.startswith("https://keiba.yahoo.co.jp/race/denma/"):
                race_denma_count += 1
                continue

            raise ContractFail("Unknown request url: url=%s" % request.url)

        if race_denma_count == 0:
            raise ContractFail("Empty race_denma request")


class RaceResultContract(Contract):
    name = "race_result"

    def post_process(self, output):
        logger.debug("RaceResultContract#post_process: start")

        # Check race payoff
        items = [o for o in output if isinstance(o, RacePayoffItem)]
        if len(items) < 1:
            raise ContractFail("RacePayoffItem is empty")

        # Check race result
        items = [o for o in output if isinstance(o, RaceResultItem)]
        if len(items) < 1:
            raise ContractFail("RaceResultItem is empty")


class RaceDenmaContract(Contract):
    name = "race_denma"

    def post_process(self, output):
        logger.debug("RaceDenmaContract#post_process: start")

        # Check requests
        requests = [o for o in output if isinstance(o, Request)]

        horse_count = 0
        trainer_count = 0
        jockey_count = 0
        odds_count = 0
        race_result_count = 0
        for request in requests:
            if request.url.startswith("https://keiba.yahoo.co.jp/directory/horse/"):
                horse_count += 1
                continue

            if request.url.startswith("https://keiba.yahoo.co.jp/directory/trainer/"):
                trainer_count += 1
                continue

            if request.url.startswith("https://keiba.yahoo.co.jp/directory/jocky/"):
                jockey_count += 1
                continue

            if request.url.startswith("https://keiba.yahoo.co.jp/odds/tfw/"):
                odds_count += 1
                continue

            if request.url.startswith("https://keiba.yahoo.co.jp/race/result/"):
                race_result_count += 1
                continue

            raise ContractFail("Unknown request url: url=%s" % request.url)

        if horse_count == 0:
            raise ContractFail("Empty horse request")

        if jockey_count == 0:
            raise ContractFail("Empty jockey request")

        if trainer_count == 0:
            raise ContractFail("Empty trainer request")

        if odds_count == 0:
            raise ContractFail("Empty odds request")

        if race_result_count == 0:
            raise ContractFail("Empty race_result request")

        # Check race info item
        items = [o for o in output if isinstance(o, RaceInfoItem)]
        if len(items) != 1:
            raise ContractFail("RaceInfoItem is not 1")

        # Check race denma item
        items = [o for o in output if isinstance(o, RaceDenmaItem)]
        if len(items) < 1:
            raise ContractFail("RaceDenmaItem is empty")


class HorseContract(Contract):
    name = "horse"

    def post_process(self, output):
        logger.debug("HorseContract#post_process: start")

        if len(output) != 1:
            raise ContractFail("output is not single")

        if not isinstance(output[0], HorseItem):
            raise ContractFail("output is not HorseItem")


class TrainerContract(Contract):
    name = "trainer"

    def post_process(self, output):
        logger.debug("TrainerContract#post_process: start")

        if len(output) != 1:
            raise ContractFail("output is not single")

        if not isinstance(output[0], TrainerItem):
            raise ContractFail("output is not TrainerItem")


class JockeyContract(Contract):
    name = "jockey"

    def post_process(self, output):
        logger.debug("JockeyContract#post_process: start")

        if len(output) != 1:
            raise ContractFail("output is not single")

        if not isinstance(output[0], JockeyItem):
            raise ContractFail("output is not JockeyItem")


class OddsWinPlaceContract(Contract):
    name = "odds_win_place"

    def post_process(self, output):
        logger.debug("OddsWinPlaceContract#post_process: start")

        if len(output) < 1:
            raise ContractFail("Empty odds")

        for request in output:
            if not isinstance(request, OddsWinPlaceItem):
                raise ContractFail("request is not OddsWinPlaceItem")
