import scrapy
from scrapy.http import TextResponse, Request, Response
import jq
import json
import requests

class TeamsSpider(scrapy.Spider):
    name = 'teams'
    domain = 'https://statsapi.web.nhl.com'
    api_root=f'{domain}/api/v1'
    start_urls = [f'{api_root}/teams']
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse_teams)

    def parse_teams(self, response: TextResponse):
        #  team_links = jq.compile(".teams[].link").input(response.text).all()
        json_response = json.loads(response.body)
        team_links = jq.compile(".teams[].link").input(json_response).all()
        for link in team_links:
            yield response.follow(link, callback=self.parse_team)

    def parse_team(self, response: TextResponse):
        json_response = json.loads(response.text)
        yield json_response

class GamesSpider(scrapy.Spider):
    name = 'games'
    domain = 'statsapi.web.nhl.com'
    api_root = f'https://{domain}/api/v1'

    def __init__(self, season=None, *args, **kwargs):
        if season:
            self.season_id=f"{season}{int(season)+1}"
        super().__init__(*args, **kwargs)

    def start_requests(self):
        if hasattr(self, "season_id"):
            yield from self.crawl_season(self.season_id)
        else:
            yield Request(url=f'{self.api_root}/seasons', callback=self.parse_seasons)

    def parse_seasons(self, response: TextResponse):
        json_response = json.loads(response.text)
        seasons = jq.compile('.seasons[].seasonId').input(json_response).all()
        for season_id in seasons:
            yield from self.crawl_season(season_id)

    def crawl_season(self, season_id: str):
        print(f"crawl season {season_id}")
        yield Request(url=f"{self.api_root}/schedule?season={season_id}",
                callback=self.parse_schedule)

    def parse_schedule(self, response: TextResponse):
        schedule = json.loads(response.text)
        game_links = jq.compile (".dates[].games[].link").input(schedule).all()
        for link in game_links:
            yield Request(url=f"https://{self.domain}{link}")

    def parse(self, response: TextResponse):
        if response.status == 200:
            yield json.loads(response.text)
