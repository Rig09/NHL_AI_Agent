from flask import Flask,render_template, request
import pandas as pd
import numpy as np

NHL_data = pd.read_csv('TotalPlayerStats.csv')


ev_team_players = ['evPlayer1', 'evPlayer2','evPlayer3', 'evPlayer4','evPlayer5', 'evPlayer6', 'evGoalie']
against_team_players = ['agPlayer1', 'agPlayer2', 'agPlayer3', 'agPlayer4', 'agPlayer5', 'agPlayer6', 'agGoalie']

playerStats = np.array(['player_name', 'goalsFor', 'assists', 'primary_points', 'primary_assists','evGoalsFor', 'evAssists', 'evPrimary_points', 'evPrimaryAssists', 'chancesFor', 
                        'chancesOnIceFor', "onIceGoalsFor", 'chancesOnIceAg', 'onIceGoalsAgainst', 'chancePercentage', 'goalPercentage',  'evchancesFor',
                        'evchancesOnIceFor','evonIceGoalsFor', 'evchancesOnIceAg', 'evonIceGoalsAgainst', 'evchancePercentage', 'evgoalPercentage', 'hits', 'blocks', 'takeaways', 'giveaways', 
                        'takeToGiveRatio', 'assist_to_giveaway', 'defGive', 'neuGive','offGive', 'defTake', 'neuTake', 'offTake'])

playerVals = [0] * len(playerStats)
Percentiles = [0] * len(playerStats)
PlayerRank = [0] * len(playerStats)
Colours = [0] * len(playerStats)


invPercentiles = [False, False, False, False, False, False, False, False, False, False, False, False, True, True, False, False, False, False, False, False, True,
                   True, False, False, False, False, True, False, False, True, True, True, False, False, False]

def find_percentile(arr, item):
    sorted_arr = sorted(arr)
    
    index = sorted_arr.index(item)
    
    percentile = (index + 1) / len(sorted_arr) * 100
    
    return percentile

def player_rank(arr, item):
    sorted_arr = sorted(arr)
    
    index = len(sorted_arr) - sorted_arr.index(item)
    return index

app = Flask(__name__)

@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/result", methods =['POST', 'GET'])
def result():
    output = request.form.to_dict()
    player_name = output["name"]
    for i in range(len(playerVals)):
        playerVals[i] = NHL_data.loc[NHL_data['player_name'] == player_name, playerStats[i]].values[0]
        Percentiles[i] = round(find_percentile(NHL_data[playerStats[i]], playerVals[i]), 2)
        PlayerRank[i] = player_rank(NHL_data[playerStats[i]], playerVals[i])
        if invPercentiles[i]:
            Percentiles[i] = round(100 - Percentiles[i], 2)
        if i > 1 :
             playerVals[i] = round(playerVals[i], 2)
        if Percentiles[i] > 50:
            Colours[i] = (0, ((Percentiles[i] - 50)*255)/50, 0)
        else :
            Colours[i] = ((Percentiles[i] * 255)/50, 0, 0)
         

    return render_template("result.html", name = player_name, playerVals = playerVals, Percentiles = Percentiles, 
                           Ranks = PlayerRank, inputColours = Colours)

if __name__ == '__main__':
        app.run(debug= True, port=5001)