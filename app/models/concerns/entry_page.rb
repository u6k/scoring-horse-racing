class EntryPage
  extend ActiveSupport::Concern

  attr_reader :entry_id, :entries

  def initialize(entry_id, content = nil)
    @entry_id = entry_id
    @content = content

    @downloader = Crawline::Downloader.new("scoring-horse-racing/0.0.0 (https://github.com/u6k/scoring-horse-racing")

    @repo = Crawline::ResourceRepository.new(
      Rails.application.secrets.s3_access_key,
      Rails.application.secrets.s3_secret_key,
      Rails.application.secrets.s3_region,
      Rails.application.secrets.s3_bucket,
      Rails.application.secrets.s3_endpoint,
      true)

    _parse
  end

  def download_from_web!
    @content = @downloader.download_with_get(_build_url)

    _parse
  end

  def download_from_s3!
    @content = @repo.get_s3_object(_build_s3_path)

    _parse
  end

  def valid?
    ((not @entry_id.nil?) \
      && (not @entries.nil?))
  end

  def exists?
    @repo.exists_s3_object?(_build_s3_path)
  end

  def save!
    if not valid?
      raise "Invalid"
    end

    @repo.put_s3_object(_build_s3_path, @content)
  end

  def same?(obj)
    if not obj.instance_of?(EntryPage)
      return false
    end

    if @entry_id != obj.entry_id \
      || @entries.nil? != obj.entries.nil?
      return false
    end

    true
  end

  private

  def _parse
    if @content.nil?
      return nil
    end

    doc = Nokogiri::HTML.parse(@content, nil, "UTF-8")

    @entries = doc.xpath("//table[contains(@class, 'denmaLs')]/tr").map do |tr|
      entry = {}

      tr.xpath("td[@class='txC']/span[contains(@class, 'wk')]").each do |span|
        span.text.match(/^([0-9]+)$/) do |bracket_number|
          entry[:bracket_number] = bracket_number[1].to_i
        end
      end

      tr.xpath("td[@class='txC fntB']/strong").each do |strong|
        strong.text.match(/^([0-9]+)$/) do |horse_number|
          entry[:horse_number] = horse_number[1].to_i
        end
      end

      tr.xpath("td[@class='fntN']").each do |td|
        td.at_xpath("a")["href"].match(/^\/directory\/horse\/([0-9]+)\/$/) do |horse_id|
          entry[:horse] = HorsePage.new(horse_id[1])
        end

        td.at_xpath("span[@class='fntSS']/a")["href"].match(/^\/directory\/trainer\/([0-9]+)\/$/) do |trainer_id|
          entry[:trainer] = TrainerPage.new(trainer_id[1])
        end
      end

      tr.xpath("td[@class='txC']/a").each do |a|
        a["href"].match(/^\/directory\/jocky\/([0-9]+)\/$/) do |jockey_id|
          entry[:jockey] = JockeyPage.new(jockey_id[1])
        end
      end

      if entry[:bracket_number].nil?
        nil
      else
        entry
      end
    end

    @entries.compact!
    if @entries.empty?
      @entries = nil
    end
  end

  def _build_url
    "https://keiba.yahoo.co.jp/race/denma/#{@entry_id}/"
  end

  def _build_s3_path
    Rails.application.secrets.s3_folder + "/entry/entry.#{@entry_id}.html"
  end

end
