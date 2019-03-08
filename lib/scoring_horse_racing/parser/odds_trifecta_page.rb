require "nokogiri"
require "crawline"

module ScoringHorseRacing::Parser
  class OddsTrifectaPageParser < Crawline::BaseParser
    def initialize(url, data)
      @logger = ScoringHorseRacing::AppLogger.get_logger
      @logger.info("OddsTrifectaPageParser#initialize: start: url=#{url}, data.size=#{data.size}")

      _parse(url, data)
    end

    def redownload?
      @logger.debug("OddsTrifectaPageParser#redownload?: start")

      base_date = Time.now - 60 * 60 * 24 * 90
      date = Time.local(@start_datetime.year, @start_datetime.month, @start_datetime.day)

      @logger.debug("OddsTrifectaPageParser#redownload?: base_date=#{base_date}, date=#{date}")

      (base_date < date)
    end

    def valid?
      (@title === "3連単")
    end

    def related_links
      @related_links
    end

    def parse(context)
      # TODO: Parse all result info
      context["odds_trifecta"] = {
        @odds_trifecta_id => {
          @uma_ban => {}
        }
      }
    end

    private

    def _parse(url, data)
      @logger.debug("OddsTrifectaPageParser#_parse: start")

      url.match(/^.+?\/odds\/st\/([0-9]+)\/(\?umaBan=([0-9]+))?$/) do |parts|
        @odds_trifecta_id = parts[1]
        @uma_ban = parts[3] || "1"
      end
      @logger.info("OddsTrifectaPageParser#_parse: @odds_trifecta_id=#{@odds_trifecta_id}, @uma_ban=#{@uma_ban}")

      doc = Nokogiri::HTML.parse(data, nil, "UTF-8")

      doc.xpath("//li[@id='raceNavi2C']").each do |li|
        @logger.debug("OddsTrifectaPageParser#_parse: li=#{li.inspect}")

        @title = li.children[0].text.strip
        @logger.info("OddsTrifectaPageParser#_parse: @title=#{@title}")
      end

      doc.xpath("//p[@id='raceTitDay']").each do |p|
        @logger.debug("OddsTrifectaPageParser#_parse: p")

        date = p.children[0].text.strip.match(/^([0-9]+)年([0-9]+)月([0-9]+)日/) do |date_parts|
          Time.new(date_parts[1].to_i, date_parts[2].to_i, date_parts[3].to_i)
        end

        time = p.children[4].text.strip.match(/^([0-9]+):([0-9]+)発走/) do |time_parts|
          Time.new(1900, 1, 1, time_parts[1].to_i, time_parts[2].to_i, 0)
        end

        if (not date.nil?) && (not time.nil?)
          @start_datetime = Time.new(date.year, date.month, date.day, time.hour, time.min, 0)
          @logger.info("OddsTrifectaPageParser#_parse: @start_datetime=#{@start_datetime}")
        end
      end

      @related_links = doc.xpath("//div[@id='raceNavi2']/ul/li").map do |li|
        if not li.children[0]["href"].nil?
          li.children[0]["href"].match(/^(\/odds\/.+?\/[0-9]+\/).*$/) do |path|
            @logger.debug("OddsTrifectaPageParser#_parse: path=#{path.inspect}")
            URI.join(url, path[1]).to_s
          end
        end
      end

      @related_links += doc.xpath("//select[@name='umaBan']/option").map do |option|
        URI.join(url, "?umaBan=#{option["value"]}").to_s if option["selected"].nil?
      end

      @related_links.compact!

      @related_links.each do |related_link|
        @logger.info("OddsTrifectaPageParser#_parse: related_link=#{related_link}")
      end
    end
  end
end