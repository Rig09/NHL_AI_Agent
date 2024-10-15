import pandas as pd

# Load data from CSV file
NHL_data = pd.read_csv('PredictedVals.csv')
block_data = pd.read_csv('block_data.csv')
hit_data = pd.read_csv('hit_data.csv')
tg_data = pd.read_csv('tg_data.csv')
assist_data = pd.read_csv('assist_data.csv')
null_data = pd.read_csv('nullLocationShots.csv')

ev_team_players = ['evPlayer1', 'evPlayer2','evPlayer3', 'evPlayer4','evPlayer5', 'evPlayer6', 'evGoalie']
against_team_players = ['agPlayer1', 'agPlayer2', 'agPlayer3', 'agPlayer4', 'agPlayer5', 'agPlayer6', 'agGoalie']

#assistPlayers = ['p2_name', 'p3_name']

playerStats = ['player_name', 'goalsFor', 'assists', 'primary_points', 'primary_assists','evGoalsFor', 'evAssists', 'evPrimary_points', 'evPrimaryAssists', 'chancesFor', 
               'chancesOnIceFor', "onIceGoalsFor", 'chancesOnIceAg', 'onIceGoalsAgainst', 'chancePercentage', 'goalPercentage',  'evchancesFor',
                'evchancesOnIceFor','evonIceGoalsFor', 'evchancesOnIceAg', 'evonIceGoalsAgainst', 'evchancePercentage', 'evgoalPercentage', 'hits', 'blocks', 'takeaways', 'giveaways', 
               'takeToGiveRatio', 'assist_to_giveaway', 'defGive', 'neuGive','offGive', 'defTake', 'neuTake', 'offTake']

playerStats_df = pd.DataFrame(columns=playerStats)

nullPrediction = null_data['Event'].sum() / len(null_data)
evNHL_data = NHL_data[NHL_data['Strength_5x5'].eq(1)]
evnull_data = null_data[null_data['Strength_5x5'].eq(1)]
evassist_data = assist_data[assist_data['Strength_5x5'].eq(1)]
def calculate_player_stats(player_name, playerStats_df):
    onIcenullShots = null_data[null_data[ev_team_players].eq(player_name).any(axis=1)]
    onIcenullShotsAgainst = null_data[null_data[against_team_players].eq(player_name).any(axis=1)]
    nullShotsFor = null_data[null_data['p1_name'].eq(player_name)]
    chancesOnIceFor_data = NHL_data[NHL_data[ev_team_players].eq(player_name).any(axis=1)]
    chancesOnIceAgainst_data = NHL_data[NHL_data[against_team_players].eq(player_name).any(axis=1)]
    chancesFor_data = NHL_data[NHL_data['p1_name'].eq(player_name)]
    #repeat for 5v5 data
    evonIcenullShots = evnull_data[evnull_data[ev_team_players].eq(player_name).any(axis=1)]
    evonIcenullShotsAgainst = evnull_data[evnull_data[against_team_players].eq(player_name).any(axis=1)]
    evnullShotsFor = evnull_data[evnull_data['p1_name'].eq(player_name)]
    evchancesOnIceFor_data = evNHL_data[evNHL_data[ev_team_players].eq(player_name).any(axis=1)]
    evchancesOnIceAgainst_data = evNHL_data[evNHL_data[against_team_players].eq(player_name).any(axis=1)]
    evchancesFor_data = evNHL_data[evNHL_data['p1_name'].eq(player_name)]

    goalsFor = chancesFor_data['Event'].sum() + nullShotsFor['Event'].sum()
    a2data = assist_data[assist_data['p3_name'].eq(player_name)]
    a1data = assist_data[assist_data['p2_name'].eq(player_name)]
    assists = len(a1data) + len(a2data)
    primary_assists = len(a1data)
    primary_points = primary_assists + goalsFor #Next repeat the above at even strength

    evGoalsFor = evchancesFor_data['Event'].sum() + evnullShotsFor['Event'].sum()
    eva2data = evassist_data[evassist_data['p3_name'].eq(player_name)]
    eva1data = evassist_data[evassist_data['p2_name'].eq(player_name)]
    evAssists = len(eva1data) + len(eva2data)
    evPrimaryAssists =  len(eva1data)
    evPrimary_points = evPrimaryAssists + evGoalsFor

    chancesFor = chancesFor_data['Prediction'].sum() + (len(nullShotsFor) * nullPrediction)
    chancesOnIceFor = chancesOnIceFor_data['Prediction'].sum() + (len(onIcenullShots) * nullPrediction)
    onIceGoalsFor = chancesOnIceFor_data['Event'].sum() + onIcenullShots['Event'].sum()
    chancesOnIceAg = chancesOnIceAgainst_data['Prediction'].sum() + (len(onIcenullShotsAgainst) * nullPrediction)
    onIceGoalsAgainst = chancesOnIceAgainst_data['Event'].sum() + onIcenullShotsAgainst['Event'].sum()
    chancePercentage = (chancesOnIceFor/ (chancesOnIceAg + chancesOnIceFor)) * 100
    if onIceGoalsFor + onIceGoalsAgainst != 0:
        goalPercentage = (onIceGoalsFor/ (onIceGoalsFor + onIceGoalsAgainst)) * 100
    else:
        goalPercentage = 0

    evchancesFor = evchancesFor_data['Prediction'].sum() + (len(evnullShotsFor) * nullPrediction)
    evchancesOnIceFor = evchancesOnIceFor_data['Prediction'].sum() + (len(evonIcenullShots) * nullPrediction)
    evonIceGoalsFor = evchancesOnIceFor_data['Event'].sum() + evonIcenullShots['Event'].sum()
    evchancesOnIceAg = evchancesOnIceAgainst_data['Prediction'].sum() + (len(evonIcenullShotsAgainst) * nullPrediction)
    evonIceGoalsAgainst = evchancesOnIceAgainst_data['Event'].sum() + evonIcenullShotsAgainst['Event'].sum()
    evchancePercentage = (evchancesOnIceFor/ (evchancesOnIceAg + evchancesOnIceFor)) * 100
    if evonIceGoalsFor + evonIceGoalsAgainst != 0:
        evgoalPercentage = (evonIceGoalsFor/ (evonIceGoalsFor + evonIceGoalsAgainst)) * 100
    else:
        evgoalPercentage = 0
    

    playerHit_data = hit_data[hit_data['p1_name'].eq(player_name)]
    hits = len(playerHit_data)
    playerBlock_data = block_data[block_data['p1_name'].eq(player_name)]
    blocks = len(playerBlock_data)

    playertg = tg_data.loc[hit_data['p1_name'] == player_name]
    takeaways = playertg['Event'].sum()
    giveaways = len(playertg) - takeaways
    if takeaways + giveaways != 0:
        takeToGiveRatio = takeaways/len(playertg)
    else:
        takeToGiveRatio = 0
    if giveaways != 0:
        assist_to_giveaway = assists/giveaways
    else:
        assist_to_giveaway = assists

    offData = playertg[playertg['Ev_Zone'] == 'Off']
    offGive = offData['Event'].sum()
    offTake = len(offData) - offGive

    neuData = playertg[playertg['Ev_Zone'] == 'Neu']
    neuGive = neuData['Event'].sum()
    neuTake = len(neuData) - neuGive

    defData = playertg[playertg['Ev_Zone'] == 'Def']
    defGive = defData['Event'].sum()
    defTake = len(defData) - defGive

    

    newRow = [player_name, goalsFor, assists, primary_points, primary_assists, evGoalsFor, evAssists, evPrimary_points, evPrimaryAssists,
               chancesFor, chancesOnIceFor, onIceGoalsFor, chancesOnIceAg, onIceGoalsAgainst, chancePercentage, goalPercentage, evchancesFor,
                evchancesOnIceFor,evonIceGoalsFor, evchancesOnIceAg, evonIceGoalsAgainst, evchancePercentage, evgoalPercentage, hits, blocks,
               takeaways, giveaways, takeToGiveRatio, assist_to_giveaway, defGive, neuGive, offGive, defTake, neuTake, offTake]
    playerStats_df.loc[len(playerStats_df)] = newRow
    return playerStats_df


unique_players = NHL_data['p1_name'].unique()
#print(len(unique_players))
for player in unique_players:
    playerStats_df = calculate_player_stats(player, playerStats_df)


playerStats_df.to_csv('TotalPlayerStats.csv', index=False)