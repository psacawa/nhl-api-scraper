import scrapy
from scrapy.http import TextResponse, Request, Response
import jq
import json

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
    api_root = 'https://{domain}/api/v1'
    # contains an upper bound for the number of games in a season+gameType
    #  as discovered at a certain point of a progressive crawl
    games_limit = {}

    def __init__(self, season=None, *args, **kwargs):
        self.season=season
        super().__init__(*args, **kwargs)

    def start_requests(self):
        if self.season:
            yield from self.crawl_season(self.season)
        else:
            yield Request(url=f'{self.api_root}/seasons', callback=self.parse_seasons)

    def parse_seasons(self, response: TextResponse):
        json_response = json.loads(response.text)
        seasons = jq.compile('.seasons[].seasonId[:4]').input(json_response).all()
        for season in seasons:
            yield from self.crawl_season(season)

    def crawl_season(self, season: str):
        yield from self.crawl_preseason(season)
        yield from self.crawl_regular_season(season)
        yield from self.crawl_playoffs(season)

    def crawl_preseason(self, season: str):
        yield from self.crawl_progressive(f"{season}01", 150)

    def crawl_regular_season(self, season: str):
        yield from self.crawl_progressive(f"{season}02", 1200)

    def crawl_progressive(self, key: str, limit: int):
        """
        For pre and regular seasons, when the # of games is uncertain, we have a
        progressive crawl, which crawls with increasing indice, and stops if the indice
        reaches the upper limit. This upper limit is hardcoded from above, and can
        decrease when a crawl at a certain indice 404s.
        """
        self.games_limit[key] = limit
        for i in range(limit):
            game_id = f"{key}{i:04}"
            if i >= self.games_limit[key]:
                break
            yield Request(url=f"{self.api_root}/game/{game_id}/feed/live",
                    callback=self.parse_progressive, cb_kwargs={"key": key, "idx": i})

    def parse_progressive(self, response: TextResponse, key, idx):
        if response.status != 200:
            self.games_limit['key'] = min (self.games_limit['key'], idx)
        else:
            yield json.loads(response.text)
               

    def crawl_playoffs(self, season: str):
        

    def parse(self, response: TextResponse):
        if response.status == 200:
            yield json.loads(response.text)
