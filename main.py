import datetime
import os
import sys
import traceback
import urllib.request
import json
import time
import dateutil.parser
import pandas as pd
from threading import Timer
from collections import OrderedDict
import streamlit as st
import matplotlib
import matplotlib.pyplot as plt
from PIL import Image
import seaborn as sns
import numpy as np

MAX_DELAY = int(os.getenv('MAX_DELAY', 10))
MIN_DELAY = int(os.getenv('MIN_DELAY', 10))

st.set_page_config(layout='wide')
st.sidebar.header("Select Team")

NHL = os.getenv('NHL', 'true').lower() == 'true'


class NHLGame:
    def __init__(self, home, away, home_score, away_score, home_shots, away_shots, home_PP, away_PP, game_date):
        self.home = Team(home, home_score, home_shots, home_PP)
        self.away = Team(away, away_score, away_shots, away_PP)
        self.game_date = game_date
        self.game_status = None

    def time_delay(self):
        if self.game_status == 'Live':
            return MIN_DELAY
        now = datetime.datetime.now(datetime.timezone.utc)
        time_delta = (self.game_date - now).total_seconds()
        if time_delta < 0 and self.game_status == 'Preview':
            return MIN_DELAY
        # This means the game is about to begin, collect data more frequently
        if time_delta > 0:
            return min(MAX_DELAY, time_delta)
        # This means the game is over and we should get rid of it
        return False


def IceMaker(StatFrame):
    x_co = []
    for x_tuple in StatFrame['Xco']:
        x_co.append(int(str(x_tuple[0])))

    y_co = []
    for y_tuple in StatFrame['Yco']:
        y_co.append(int(str(y_tuple[0])))

    # StatTable = StatFrame[['X', 'Y']]
    # StatTable = StatTable.groupby(["X", "Y"]).size().reset_index(name="Freq")
    #
    # x = StatTable['X']
    # y = StatTable['Y']

    x = pd.Series(x_co)
    y = pd.Series(y_co)
    ev = pd.Series(StatFrame['Label'])
    # print(x)
    # print(y)
    # print(ev)
    # for index, value in x.items():
    #     if x[index] < 0:
    #         x[index] = -x[index]
    #         y[index] = -y[index]
    #
    # freq = StatTable['Freq']
    sns.set()
    fig, ax = plt.subplots(frameon=True)

    DPI = 64
    IMG_WIDTH = 1000
    IMG_HEIGHT = 850
    fig = plt.figure(figsize=(IMG_WIDTH / DPI, IMG_HEIGHT / DPI), dpi=DPI)
    ax_extent = [-100, 100, -42.5, 42.5]
    img = Image.open('NHLArena.png')
    plt.imshow(img, extent=ax_extent)

    sns.set_style("dark")
    # ax = sns.kdeplot(x=x, y=y, cmap="icefire", fill=True, thresh=0.05, levels=100, zorder=2, alpha=0.5)
    # sns.scatterplot(x=x, y=y, s=50, alpha=1, hue=freq, palette="dark:salmon_r")
    sns.scatterplot(x=x, y=y, s=50, alpha=1, palette="dark:salmon_r")
    sns.scatterplot(x=x, y=y, s=500, alpha=0.4, palette="dark:salmon_r")

    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")
    fig.patch.set_alpha(0.0)  # Remove the labelling of axes
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.grid: True
    ax.edgecolor: .8
    ax.linewidth: 1
    ax.set(xlim=(0, 100), ylim=(-42.5, 42.5))
    p = matplotlib.patches.Rectangle(xy=[0, -42.5], width=100, height=85, transform=ax.transData,
                                     facecolor="xkcd:white", alpha=0.3, zorder=-1)

    def label_point(x, y, val, ax):
        a = pd.concat({'x': x, 'y': y, 'val': val}, axis=1)
        for i, point in a.iterrows():
            ax.text(point['x']+0.02, point['y'], str(point['val']))

    label_point(x, y, ev, plt.gca())

    for col in ax.collections:
        col.set_clip_path(p)
    plt.axis('off')
    return fig


class GamePlays:
    def __init__(self, result, x, y, team, period, time):
        self.result = result
        self.x = x
        self.y = y
        self.team = team
        self.period = period
        self.time = time


class NHLTeams:
    team_dict = {"Anaheim Ducks": "ANA",
                 "Arizona Coyotes": "ARI",
                 "Boston Bruins": "BOS",
                 "Buffalo Sabres": "BUF",
                 "Carolina Hurricanes": "CAR",
                 "Columbus Blue Jackets": "CBJ",
                 "Calgary Flames": "CGY",
                 "Chicago Blackhawks": "CHI",
                 "Colorado Avalanche": "COL",
                 "Dallas Stars": "DAL",
                 "Detroit Red Wings": "DET",
                 "Edmonton Oilers": "EDM",
                 "Florida Panthers": "FLA",
                 "Los Angeles Kings": "LAK",
                 "Minnesota Wild": "MIN",
                 "Montreal Canadiens": "MTL",
                 "Montréal Canadiens": "MTL",
                 "New Jersey Devils": "NJD",
                 "Nashville Predators": "NSH",
                 "New York Islanders": "NYI",
                 "New York Rangers": "NYR",
                 "Ottawa Senators": "OTT",
                 "Philadelphia Flyers": "PHI",
                 "Pittsburgh Penguins": "PIT",
                 "San Jose Sharks": "SJS",
                 "St. Louis Blues": "STL",
                 "Tampa Bay Lightning": "TBL",
                 "Toronto Maple Leafs": "TOR",
                 "Vancouver Canucks": "VAN",
                 "Vegas Golden Knights": "VGK",
                 "Winnipeg Jets": "WPG",
                 "Washington Capitals": "WSH"
                 }


class Team:
    def __init__(self, team_name, team_score, team_shots, team_PP, league="nhl"):
        self.team_name = team_name
        self.team_score = team_score
        self.team_shots = team_shots
        self.team_PP = team_PP

    #     self.league = league
    #     if len(team_name) <= 3:
    #         self.team_abbr = team_name
    #     else:
    #         self.team_abbr = NHLTeams.team_dict[team_name]
    #     self.team_abbr_lower = self.team_abbr.lower()
    #     self.__last_score = team_score
    #     self.last_score = team_score
    #     self.__in_power_play = False
    #     self.in_power_play = False
    #     self.team = None
    #     self.__power_play_count = None
    #     self.power_play_count = None
    #
    # @property
    # def last_score(self):
    #     return self.__last_score
    #
    # @last_score.setter
    # def last_score(self, value):
    #     if value != self.__last_score:
    #         self.notify_of_score()
    #         self.__last_score = value
    #
    # @property
    # def in_power_play(self):
    #     return self.__in_power_play
    #
    # @in_power_play.setter
    # def in_power_play(self, value):
    #     if value != self.__in_power_play:
    #         if value:
    #             self.notify_of_power_play()
    #         self.__in_power_play = value
    #
    # @property
    # def power_play_count(self):
    #     return self.__power_play_count
    #
    # @power_play_count.setter
    # def power_play_count(self, value):
    #     if value is not None:
    #         value = int(value)
    #     if self.__power_play_count is None:
    #         self.__power_play_count = value
    #     else:
    #         if value > self.__power_play_count:
    #             self.notify_of_power_play()
    #             self.__power_play_count = value
    #
    # def notify_of_score(self):
    #     print(self.last_score)
    #     print('SCORE', self.team_abbr)
    #     print(vars(self))
    #     preamble = ""
    #     if self.league != 'nhl':
    #         preamble = self.league + "_"
    #     notification = ('https://maker.ifttt.com/trigger/'
    #                     '{preamble}{team}_score/with/key/{ifttt}'.format(team=self.team_abbr_lower,
    #                                                                      ifttt=IFTTT_KEY,
    #                                                                      preamble=preamble))
    #     # Trigger local hubitat routine
    #     notification = ('http://192.168.1.66/apps/api/49/trigger?access_token=98bc3cd8-ac0c-4bb6-a01e-c0b1f2432ec1')
    #     # Trigger only if CGY
    #     # if self.team_abbr == 'CGY':
    #     self.send(notification, GOAL_DURATION)
    #
    # def notify_of_power_play(self):
    #     print('PP', self.team_abbr)
    #     preamble = ""
    #     if self.league != 'nhl':
    #         preamble = self.league + "_"
    #     notification = ('https://maker.ifttt.com/trigger/'
    #                     '{preamble}{team}_power_play/with/key/{ifttt}'.format(team=self.team_abbr_lower,
    #                                                                           ifttt=IFTTT_KEY,
    #                                                                           preamble=preamble))
    #     # Trigger local hubitat routine
    #     notification = ('http://192.168.1.66/apps/api/49/trigger?access_token=98bc3cd8-ac0c-4bb6-a01e-c0b1f2432ec1')
    #     # Trigger only if CGY
    #     # if self.team_abbr == 'CGY':
    #         # self.send(notification, POWER_PLAY_DURATION)
    #
    # def notify_of_end(self):
    #     preamble = ""
    #     if self.league != 'nhl':
    #         preamble = self.league + "_"
    #     notification = 'https://maker.ifttt.com/trigger/{event}/with/key/{ifttt}'.format(event=END_EVENT, ifttt=IFTTT_KEY)
    #     self.send(notification)
    #
    # def send(self, notification, end=None):
    #     print('Sending', notification)
    #     with urllib.request.urlopen(notification) as notify:
    #         raw_response = notify.read()
    #     if end:
    #         global END_TIMER
    #         try:
    #             END_TIMER.cancel()
    #             print('cancelled existing end timer')
    #         except:
    #             pass
    #         END_TIMER = Timer(end, self.notify_of_end)
    #         END_TIMER.start()
    #         print('started end timer for ' + str(end) + ' seconds')


ToplineString = "Today's Games:  "
PlayingTeamList = []
with urllib.request.urlopen(
        'https://statsapi.web.nhl.com/api/v1/schedule?expand=schedule.linescore') as response:
    raw_json = response.read().decode('utf8')
json_data = json.loads(raw_json)
for game in json_data['dates'][0]['games']:
    # print(game['teams']['away']['team']['name'])
    # print(game['teams']['home']['team']['name'])
    # print(stTeamPicker)
    ToplineString = ToplineString + NHLTeams.team_dict[str(game['teams']['away']['team']['name'])] + " vs. " + NHLTeams.team_dict[str(game['teams']['home']['team']['name'])] + "   "
    PlayingTeamList = PlayingTeamList + [str(game['teams']['home']['team']['name'])]
    PlayingTeamList = PlayingTeamList + [str(game['teams']['away']['team']['name'])]
st.text(ToplineString)
# st.text(PlayingTeamList)

# st.title("Game Statistics - Mini Skorboard")

GoStatus = False

stTeamPicker = st.sidebar.selectbox(label="Select Team:", options=(PlayingTeamList))
# stTeamPicker = st.sidebar.selectbox(label="Select Team:", options=('Anaheim Ducks',
#                                                                    'Arizona Coyotes',
#                                                                    'Boston Bruins',
#                                                                    'Buffalo Sabres',
#                                                                    'Carolina Hurricanes',
#                                                                    'Columbus Blue Jackets',
#                                                                    'Calgary Flames',
#                                                                    'Chicago Blackhawks',
#                                                                    'Colorado Avalanche',
#                                                                    'Dallas Stars',
#                                                                    'Detroit Red Wings',
#                                                                    'Edmonton Oilers',
#                                                                    'Florida Panthers',
#                                                                    'Los Angeles Kings',
#                                                                    'Minnesota Wild',
#                                                                    'Montréal Canadiens',
#                                                                    'New Jersey Devils',
#                                                                    'Nashville Predators',
#                                                                    'New York Islanders',
#                                                                    'New York Rangers',
#                                                                    'Ottawa Senators',
#                                                                    'Philadelphia Flyers',
#                                                                    'Pittsburgh Penguins',
#                                                                    'San Jose Sharks',
#                                                                    'St. Louis Blues',
#                                                                    'Tampa Bay Lightning',
#                                                                    'Toronto Maple Leafs',
#                                                                    'Vancouver Canucks',
#                                                                    'Vegas Golden Knights',
#                                                                    'Winnipeg Jets',
#                                                                    'Washington Capitals'))

stGoButton = st.sidebar.button("Start")

if stGoButton:
    if GoStatus == False:
        GoStatus = True
    else:
        GoStatus = False

## UI

# stContinueCheck = st.sidebar.checkbox("Stop")
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    stGameStatus = st.empty()
with col2:
    stPeriod = st.empty()
    stGameTime = st.empty()
    stPPCheck = st.empty()
with col3:
    stVenue = st.empty()

st.markdown("---")
col1, col2, col3, col4, col5 = st.columns((1, 1, 2, 1, 1))
with col1:
    stHomeLogo = st.empty()
with col2:
    stHomeScore = st.empty()
    stHomeTeam = st.empty()
    stHomeShots = st.empty()
with col3:
    st.write("Goals")
    stGoalTable = st.empty()
    st.write("Shots")
    stShotTable = st.empty()
with col4:
    stAwayScore = st.empty()
    stAwayTeam = st.empty()
    stAwayShots = st.empty()
with col5:
    stAwayLogo = st.empty()


st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    stLastPlay1 = st.empty()
    stLastPlay2 = st.empty()
    stLastPlay3 = st.empty()
    stLastPlay4 = st.empty()
    stLastPlay5 = st.empty()
with col2:
    stArena1 = st.empty()

nhl_games = dict()
nhl_simple = dict()

TeamIndex = {
    'Anaheim Ducks': 'ANA3.png',
    'Arizona Coyotes': 'ARI3.png',
    'Boston Bruins': 'BOS3.png',
    'Buffalo Sabres': 'BUF3.png',
    'Calgary Flames': 'CGY3.png',
    'Carolina Hurricanes': 'CAR3.png',
    'Chicago Blackhawks': 'CHI3.png',
    'Columbus Blue Jackets': 'CBJ3.png',
    'Colorado Avalanche': 'COL3.png',
    'Dallas Stars': 'DAL3.PNG',
    'Detroit Red Wings': 'DET3.png',
    'Edmonton Oilers': 'EDM3.png',
    'Florida Panthers': 'FLA3.png',
    'Los Angeles Kings': 'LAK3.png',
    'Minnesota Wild': 'MIN3.png',
    'Montréal Canadiens': 'MTL3.png',
    'Nashville Predators': 'NSH3.png',
    'New Jersey Devils': 'NJD3.png',
    'New York Islanders': 'NYI3.png',
    'New York Rangers': 'NYR3.png',
    'Ottawa Senators': 'OTT3.png',
    'Philadelphia Flyers': 'PHI3.png',
    'Pittsburgh Penguins': 'PIT3.png',
    'San Jose Sharks': 'SJS3.png',
    'St. Louis Blues': 'STL3.png',
    'Tampa Bay Lightning': 'TBL3.png',
    'Toronto Maple Leafs': 'TOR3.png',
    'Vancouver Canucks': 'VAN3.png',
    'Vegas Golden Knights': 'VGK3.png',
    'Washington Capitals': 'WSH3.png',
    'Winnipeg Jets': 'WPG3.png',
}

def check_nhl():
    # print("checking nhl")

    try:
        delay = MAX_DELAY
        with urllib.request.urlopen(
                'https://statsapi.web.nhl.com/api/v1/schedule?expand=schedule.linescore') as response:
            raw_json = response.read().decode('utf8')

        json_data = json.loads(raw_json)
        for game in json_data['dates'][0]['games']:
            # print(game['teams']['away']['team']['name'])
            # print(game['teams']['home']['team']['name'])
            # print(stTeamPicker)
            if game['teams']['away']['team']['name'] == stTeamPicker or game['teams']['home']['team'][
                'name'] == stTeamPicker:
                # print("----------------------")
                game_pk = game['gamePk']
                # print(game_pk)
                game_date = dateutil.parser.parse(game['gameDate'])
                live_feed = 'https://statsapi.web.nhl.com' + game['link']
                HomeShots = 0
                AwayShots = 0

                HomePeriodGoals = []
                AwayPeriodGoals = []
                HomePeriodShots = []
                AwayPeriodShots = []
                PeriodsCols = []

                periodCounter = 1
                # if 0 in game['linescore']['periods']:
                for period in game['linescore']['periods']:
                    # print(period['home']['shotsOnGoal'])
                    PeriodsCols = PeriodsCols + [periodCounter]
                    HomeShots = HomeShots + int(period['home']['shotsOnGoal'])
                    HomePeriodShots = HomePeriodShots + [int(period['home']['shotsOnGoal'])]
                    HomePeriodGoals = HomePeriodGoals + [int(period['home']['goals'])]
                    AwayShots = AwayShots + int(period['away']['shotsOnGoal'])
                    AwayPeriodShots = AwayPeriodShots + [int(period['away']['shotsOnGoal'])]
                    AwayPeriodGoals = AwayPeriodGoals + [int(period['home']['goals'])]
                    periodCounter += 1

                print(HomePeriodShots + AwayPeriodShots)
                ShotTable = pd.DataFrame(np.array([HomePeriodShots, AwayPeriodShots]), columns=PeriodsCols, index=[game['teams']['home']['team']['name'], game['teams']['away']['team']['name']])
                GoalTable = pd.DataFrame(np.array([HomePeriodGoals, AwayPeriodGoals]), columns=PeriodsCols, index=[game['teams']['home']['team']['name'], game['teams']['away']['team']['name']])
                stShotTable.write(ShotTable)
                stGoalTable.write(GoalTable)

                if game_pk not in nhl_games:
                    nhl_games[game_pk] = NHLGame(game['teams']['home']['team']['name'],
                                                 game['teams']['away']['team']['name'],
                                                 game['teams']['home']['score'],
                                                 game['teams']['away']['score'],
                                                 HomeShots,
                                                 AwayShots,
                                                 game['linescore']['teams']['home']['powerPlay'],
                                                 game['linescore']['teams']['away']['powerPlay'],
                                                 game_date)

                    if 'currentPeriodTimeRemaining' in game['linescore']:
                        PeriodTime = game['linescore']['currentPeriodTimeRemaining']
                        PeriodOrdinal = game['linescore']['currentPeriodOrdinal']
                    else:
                        PeriodTime = "PreGame"
                        PeriodOrdinal = "PreGame"

                    # stGameTime.markdown(
                    #     "<h3 style='text-align: center; color: white;'>" + PeriodTime + "</h3>",
                    #     unsafe_allow_html=True)

                    stGameTime.write(PeriodTime)

                    nhl_simple[game_pk] = {
                        "HomeTeam": game['teams']['home']['team']['name'],
                        "AwayTeam": game['teams']['away']['team']['name'],
                        "HomeScore": game['teams']['home']['score'],
                        "AwayScore": game['teams']['away']['score'],
                        "HomeShots": HomeShots,
                        "AwayShots": AwayShots,
                        "HomePowerPlay": game['linescore']['teams']['home']['powerPlay'],
                        "AwayPowerPlay": game['linescore']['teams']['away']['powerPlay'],
                        "Date": game_date,
                        "Status": game['status']['detailedState'],
                        "Venue": game['venue']['name'],
                        "Time": PeriodTime,
                        "Period": PeriodOrdinal
                    }

                    # nhl_games[game_pk].game_status = game['status']['abstractGameState']

                    game_plays = dict(dict())

                    if nhl_games[game_pk].time_delay():
                        nhl_games[game_pk].home.last_score = game['teams']['home']['score']
                        nhl_games[game_pk].away.last_score = game['teams']['away']['score']
                        nhl_games[game_pk].home.in_power_play = game['linescore']['teams']['home']['powerPlay']
                        nhl_games[game_pk].away.in_power_play = game['linescore']['teams']['away']['powerPlay']
                        # print(game['teams']['home']['team']['name'], game['teams']['home']['score'], "Shots: ", HomeShots, "PP: ", game['linescore']['teams']['home']['powerPlay'])
                        # print(game['teams']['away']['team']['name'], game['teams']['away']['score'], "Shots: ", AwayShots, "PP: ", game['linescore']['teams']['away']['powerPlay'])
                        # print(live_feed)

                    # with urllib.request.urlopen('https://statsapi.web.nhl.com/api/v1/game/2020030116/feed/live') as response:
                    with urllib.request.urlopen(live_feed) as response:
                        live_feed_raw_json = response.read().decode('utf8')
                    live_feed_json = json.loads(live_feed_raw_json)

                    stGameStatus.subheader(nhl_simple[game_pk]['Status'])

                    stHomeScore.title(str(nhl_simple[game_pk]['HomeScore']))
                    stAwayScore.title(str(nhl_simple[game_pk]['AwayScore']))

                    stHomeTeam.header(nhl_simple[game_pk]['HomeTeam'])
                    stAwayTeam.header(nhl_simple[game_pk]['AwayTeam'])
                    stHomeLogo.image(Image.open('./TeamLogos/' + TeamIndex.get(nhl_simple[game_pk]['HomeTeam'])))
                    stAwayLogo.image(Image.open('./TeamLogos/' + TeamIndex.get(nhl_simple[game_pk]['AwayTeam'])))

                    stHomeShots.subheader("Shots " + str(nhl_simple[game_pk]['HomeShots']))
                    stAwayShots.subheader("Shots " + str(nhl_simple[game_pk]['AwayShots']))

                    if nhl_simple[game_pk]['Status'] == 'In Progress':
                        if nhl_simple[game_pk]['HomePowerPlay']:
                            stPPCheck.subheader(nhl_simple[game_pk]['HomeTeam'] + " Power Play")
                        elif nhl_simple[game_pk]['AwayPowerPlay']:
                            stPPCheck.subheader(nhl_simple[game_pk]['AwayTeam'] + " Power Play")
                        else:
                            stPPCheck.subheader("Even Strength")
                    else:
                        stPPCheck.subheader("")

                    # stPeriod.header(nhl_simple[game_pk]['Period'] + " Period")
                    stPeriod.markdown("<h2 style='text-align: left; color: red;'>" + nhl_simple[game_pk][
                        'Period'] + " Period" + "</h1>", unsafe_allow_html=True)
                    # stGameTime.header(nhl_simple[game_pk]['Time'])
                    # stGameTime.markdown(
                    #     "<h3 style='text-align: center; color: white;'>" + nhl_simple[game_pk]['Time'] + "</h3>",
                    #     unsafe_allow_html=True)
                    stVenue.subheader(nhl_simple[game_pk]['Venue'])



                    PlayCount = 0

                    game_plays[game_pk] = {}
                    for Play in live_feed_json['liveData']['plays']['allPlays']:
                        if 'x' in Play['coordinates']:
                            x_coord = Play['coordinates']['x']
                        else:
                            x_coord = 0
                        if 'y' in Play['coordinates']:
                            y_coord = Play['coordinates']['y']
                        else:
                            y_coord = 0
                        if 'team' in Play:
                            TeamCode = Play['team']['triCode']
                        else:
                            TeamCode = "NA"

                        game_plays[game_pk][PlayCount] = {}

                        game_plays[game_pk][PlayCount]["Description"] = Play['result']['description']
                        game_plays[game_pk][PlayCount]["Event"] = Play['result']['event']
                        game_plays[game_pk][PlayCount]["X"] = int(x_coord),
                        game_plays[game_pk][PlayCount]["Y"] = int(y_coord),
                        game_plays[game_pk][PlayCount]["Team"] = TeamCode,
                        game_plays[game_pk][PlayCount]["Period"] = Play['about']['period'],
                        game_plays[game_pk][PlayCount]["Time"] = Play['about']['periodTimeRemaining']

                        PlayCount += 1

                    LastPlay1 = dict()
                    LastPlay2 = dict()
                    LastPlay3 = dict()
                    LastPlay4 = dict()
                    LastPlay5 = dict()
                    LastPlay6 = dict()
                    LastPlay7 = dict()
                    LastPlay8 = dict()
                    LastPlay9 = dict()
                    LastPlay10 = dict()

                    ## Initialize Descriptions
                    LastPlay1['Description'] = ""
                    LastPlay2['Description'] = ""
                    LastPlay3['Description'] = ""
                    LastPlay4['Description'] = ""
                    LastPlay5['Description'] = ""
                    LastPlay6['Description'] = ""
                    LastPlay7['Description'] = ""
                    LastPlay8['Description'] = ""
                    LastPlay9['Description'] = ""
                    LastPlay10['Description'] = ""
                    LastPlay1['Event'] = ""
                    LastPlay2['Event'] = ""
                    LastPlay3['Event'] = ""
                    LastPlay4['Event'] = ""
                    LastPlay5['Event'] = ""
                    LastPlay6['Event'] = ""
                    LastPlay7['Event'] = ""
                    LastPlay8['Event'] = ""
                    LastPlay9['Event'] = ""
                    LastPlay10['Event'] = ""
                    LastPlay1['Time'] = ""
                    LastPlay2['Time'] = ""
                    LastPlay3['Time'] = ""
                    LastPlay4['Time'] = ""
                    LastPlay5['Time'] = ""
                    LastPlay6['Time'] = ""
                    LastPlay7['Time'] = ""
                    LastPlay8['Time'] = ""
                    LastPlay9['Time'] = ""
                    LastPlay10['Time'] = ""
                    LastPlay1['X'] = ""
                    LastPlay2['X'] = ""
                    LastPlay3['X'] = ""
                    LastPlay4['X'] = ""
                    LastPlay5['X'] = ""
                    LastPlay6['X'] = ""
                    LastPlay7['X'] = ""
                    LastPlay8['X'] = ""
                    LastPlay9['X'] = ""
                    LastPlay10['X'] = ""
                    LastPlay1['Y'] = ""
                    LastPlay2['Y'] = ""
                    LastPlay3['Y'] = ""
                    LastPlay4['Y'] = ""
                    LastPlay5['Y'] = ""
                    LastPlay6['Y'] = ""
                    LastPlay7['Y'] = ""
                    LastPlay8['Y'] = ""
                    LastPlay9['Y'] = ""
                    LastPlay10['Y'] = ""

                    if PlayCount == 0:
                        LastPlay1['Description'] = "Game Not Started"
                    elif PlayCount == 1:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                    elif PlayCount == 2:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                    elif PlayCount == 3:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                        LastPlay3 = game_plays[game_pk][PlayCount - 3]
                    elif PlayCount == 4:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                        LastPlay3 = game_plays[game_pk][PlayCount - 3]
                        LastPlay4 = game_plays[game_pk][PlayCount - 4]
                    elif PlayCount == 5:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                        LastPlay3 = game_plays[game_pk][PlayCount - 3]
                        LastPlay4 = game_plays[game_pk][PlayCount - 4]
                        LastPlay5 = game_plays[game_pk][PlayCount - 5]
                    elif PlayCount == 6:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                        LastPlay3 = game_plays[game_pk][PlayCount - 3]
                        LastPlay4 = game_plays[game_pk][PlayCount - 4]
                        LastPlay5 = game_plays[game_pk][PlayCount - 5]
                        LastPlay6 = game_plays[game_pk][PlayCount - 6]
                    elif PlayCount == 7:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                        LastPlay3 = game_plays[game_pk][PlayCount - 3]
                        LastPlay4 = game_plays[game_pk][PlayCount - 4]
                        LastPlay5 = game_plays[game_pk][PlayCount - 5]
                        LastPlay6 = game_plays[game_pk][PlayCount - 6]
                        LastPlay7 = game_plays[game_pk][PlayCount - 7]
                    elif PlayCount == 8:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                        LastPlay3 = game_plays[game_pk][PlayCount - 3]
                        LastPlay4 = game_plays[game_pk][PlayCount - 4]
                        LastPlay5 = game_plays[game_pk][PlayCount - 5]
                        LastPlay6 = game_plays[game_pk][PlayCount - 6]
                        LastPlay7 = game_plays[game_pk][PlayCount - 7]
                        LastPlay8 = game_plays[game_pk][PlayCount - 8]
                    elif PlayCount == 9:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                        LastPlay3 = game_plays[game_pk][PlayCount - 3]
                        LastPlay4 = game_plays[game_pk][PlayCount - 4]
                        LastPlay5 = game_plays[game_pk][PlayCount - 5]
                        LastPlay6 = game_plays[game_pk][PlayCount - 6]
                        LastPlay7 = game_plays[game_pk][PlayCount - 7]
                        LastPlay8 = game_plays[game_pk][PlayCount - 8]
                        LastPlay9 = game_plays[game_pk][PlayCount - 9]
                    else:
                        LastPlay1 = game_plays[game_pk][PlayCount - 1]
                        LastPlay2 = game_plays[game_pk][PlayCount - 2]
                        LastPlay3 = game_plays[game_pk][PlayCount - 3]
                        LastPlay4 = game_plays[game_pk][PlayCount - 4]
                        LastPlay5 = game_plays[game_pk][PlayCount - 5]
                        LastPlay6 = game_plays[game_pk][PlayCount - 6]
                        LastPlay7 = game_plays[game_pk][PlayCount - 7]
                        LastPlay8 = game_plays[game_pk][PlayCount - 8]
                        LastPlay9 = game_plays[game_pk][PlayCount - 9]
                        LastPlay10 = game_plays[game_pk][PlayCount - 10]


                    stLastPlay1.text(LastPlay1['Time'] + " " + LastPlay1['Event'] + ": " + LastPlay1['Description'])
                    stLastPlay2.text(LastPlay2['Time'] + " " + LastPlay2['Event'] + ": " + LastPlay2['Description'])
                    stLastPlay3.text(LastPlay3['Time'] + " " + LastPlay3['Event'] + ": " + LastPlay3['Description'])
                    stLastPlay4.text(LastPlay4['Time'] + " " + LastPlay4['Event'] + ": " + LastPlay4['Description'])
                    stLastPlay5.text(LastPlay5['Time'] + " " + LastPlay5['Event'] + ": " + LastPlay5['Description'])

                    # Create Pandas DataFrame of Recent Events


                    ######## WORK HERE, CREATE NUMPY ARRAY WITH INFORMATION FOR THE ICEMAKER
                    PlayFrame = {'Play': ["Last Play", "2nd Last Play", "3rd Last Play", "4th Last Play",
                                          "5th Last Play", "6th Last Play", "7th Last Play", "8th Last Play",
                                          "9th Last Play", "10th Last Play"],
                                 'Time': [LastPlay1['Time'], LastPlay2['Time'], LastPlay3['Time'], LastPlay4['Time'],
                                          LastPlay5['Time'], LastPlay6['Time'], LastPlay7['Time'], LastPlay8['Time'],
                                          LastPlay9['Time'], LastPlay10['Time']],
                                 'Event': [LastPlay1['Event'], LastPlay2['Event'], LastPlay3['Event'],
                                           LastPlay4['Event'], LastPlay5['Event'], LastPlay6['Event'],
                                           LastPlay7['Event'], LastPlay8['Event'], LastPlay9['Event'],
                                           LastPlay10['Event']],
                                 'Team': [LastPlay1['Team'], LastPlay2['Team'], LastPlay3['Team'],
                                           LastPlay4['Team'], LastPlay5['Team'], LastPlay6['Team'],
                                           LastPlay7['Team'], LastPlay8['Team'], LastPlay9['Team'],
                                           LastPlay10['Team']],
                                 'Label': [str(LastPlay1['Team'][0]) + ":" + str(LastPlay1['Event']),
                                           str(LastPlay2['Team'][0]) + ":" + str(LastPlay2['Event']),
                                           str(LastPlay3['Team'][0]) + ":" + str(LastPlay3['Event']),
                                           str(LastPlay4['Team'][0]) + ":" + str(LastPlay4['Event']),
                                           str(LastPlay5['Team'][0]) + ":" + str(LastPlay5['Event']),
                                           str(LastPlay6['Team'][0]) + ":" + str(LastPlay6['Event']),
                                           str(LastPlay7['Team'][0]) + ":" + str(LastPlay7['Event']),
                                           str(LastPlay8['Team'][0]) + ":" + str(LastPlay8['Event']),
                                           str(LastPlay9['Team'][0]) + ":" + str(LastPlay9['Event']),
                                           str(LastPlay10['Team'][0]) + ":" + str(LastPlay10['Event'])],
                                 'Xco': [LastPlay1['X'], LastPlay2['X'], LastPlay3['X'], LastPlay4['X'], LastPlay5['X'],
                                         LastPlay6['X'], LastPlay7['X'], LastPlay8['X'], LastPlay9['X'], LastPlay10['X']],
                                 'Yco': [LastPlay1['Y'], LastPlay2['Y'], LastPlay3['Y'], LastPlay4['Y'], LastPlay5['Y'],
                                         LastPlay6['Y'], LastPlay7['Y'], LastPlay8['Y'], LastPlay9['Y'], LastPlay10['Y']]
                    }

                    # PlayFrame = np.array([[LastPlay1['Time'],LastPlay1['Event'],LastPlay1['X'],LastPlay1['Y']],
                    #                      [LastPlay2['Time'],LastPlay2['Event'],LastPlay2['X'],LastPlay2['Y']],
                    #                      [LastPlay3['Time'],LastPlay3['Event'],LastPlay3['X'],LastPlay3['Y']],
                    #                      [LastPlay4['Time'],LastPlay4['Event'],LastPlay4['X'],LastPlay4['Y']],
                    #                      [LastPlay5['Time'],LastPlay5['Event'],LastPlay5['X'],LastPlay5['Y']]])

                    stArena1.pyplot(IceMaker(PlayFrame))

                    # stGameStatus.subheader(nhl_simple[game_pk]['Status'])
                    #
                    # stHomeScore.title(str(nhl_simple[game_pk]['HomeScore']))
                    # stAwayScore.title(str(nhl_simple[game_pk]['AwayScore']))
                    #
                    # stHomeTeam.header(nhl_simple[game_pk]['HomeTeam'])
                    # stAwayTeam.header(nhl_simple[game_pk]['AwayTeam'])
                    # stHomeLogo.image(Image.open('./TeamLogos/' + TeamIndex.get(nhl_simple[game_pk]['HomeTeam'])))
                    # stAwayLogo.image(Image.open('./TeamLogos/' + TeamIndex.get(nhl_simple[game_pk]['AwayTeam'])))
                    #
                    # stHomeShots.subheader("Shots " + str(nhl_simple[game_pk]['HomeShots']))
                    # stAwayShots.subheader("Shots " + str(nhl_simple[game_pk]['AwayShots']))
                    #
                    # if nhl_simple[game_pk]['Status'] == 'In Progress':
                    #     if nhl_simple[game_pk]['HomePowerPlay']:
                    #         stPPCheck.subheader(nhl_simple[game_pk]['HomeTeam'] + " Power Play")
                    #     elif nhl_simple[game_pk]['AwayPowerPlay']:
                    #         stPPCheck.subheader(nhl_simple[game_pk]['AwayTeam'] + " Power Play")
                    #     else:
                    #         stPPCheck.subheader("Even Strength")
                    # else:
                    #     stPPCheck.subheader("")
                    #
                    # # stPeriod.header(nhl_simple[game_pk]['Period'] + " Period")
                    # stPeriod.markdown("<h1 style='text-align: center; color: red;'>" + nhl_simple[game_pk][
                    #     'Period'] + " Period" + "</h1>", unsafe_allow_html=True)
                    # stGameTime.header(nhl_simple[game_pk]['Time'])
                    # stGameTime.markdown(
                    #     "<h3 style='text-align: center; color: white;'>" + nhl_simple[game_pk]['Time'] + "</h3>",
                    #     unsafe_allow_html=True)
                    # stVenue.subheader(nhl_simple[game_pk]['Venue'])

                    # stLastPlay1.text(LastPlay1['Time'] + " " + LastPlay1['Event'] + ": " + LastPlay1['Description'])
                    # stLastPlay2.text(LastPlay2['Time'] + " " + LastPlay2['Event'] + ": " + LastPlay2['Description'])
                    # stLastPlay3.text(LastPlay3['Time'] + " " + LastPlay3['Event'] + ": " + LastPlay3['Description'])
                    # stLastPlay4.text(LastPlay4['Time'] + " " + LastPlay4['Event'] + ": " + LastPlay4['Description'])
                    # stLastPlay5.text(LastPlay5['Time'] + " " + LastPlay5['Event'] + ": " + LastPlay5['Description'])
                    #
        for k in list(nhl_games.keys()):
            d = nhl_games[k].time_delay()
            if not d:
                del nhl_games[k]
            else:
                delay = min(d, delay)
        return delay
    except IndexError:
        return MAX_DELAY
    except Exception as e:
        # If anything goes wrong with the load then retry in MIN_DELAY sec
        print('Exception', e)
        traceback.print_exc()
        return MIN_DELAY

if stGoButton:
    while GoStatus:
        delay_for_repeat = MAX_DELAY
        if NHL:
            delay_for_repeat = min(delay_for_repeat, check_nhl())
        print("delaying for " + str(delay_for_repeat) + " seconds")
        sys.stdout.flush()
        time.sleep(delay_for_repeat)
