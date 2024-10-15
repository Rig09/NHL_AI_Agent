import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# Load data from CSV file
NHL_data = pd.read_csv('TotalPlayerStats.csv')

# Define a list of player names of interest
player_name = input("Enter the player name: ")

ev_team_players = ['evPlayer1', 'evPlayer2','evPlayer3', 'evPlayer4','evPlayer5', 'evPlayer6', 'evGoalie']
against_team_players = ['agPlayer1', 'agPlayer2', 'agPlayer3', 'agPlayer4', 'agPlayer5', 'agPlayer6', 'agGoalie']

playerStats = np.array(['goalsFor',  'assists', 'primary_points', 'primary_assists', 'chancesFor', 'chancesOnIceFor', "onIceGoalsFor", 'chancesOnIceAg', 'onIceGoalsAgainst', 
                        'chancePercentage', 'goalPercentage', 'hits', 'blocks', 'takeaways', 'giveaways', 'takeToGiveRatio', 'assist_to_giveaway', 'defGive', 
                        'neuGive','offGive', 'defTake', 'neuTake', 'offTake'])

playerVals = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
Percentiles = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

def find_percentile(arr, item):
    sorted_arr = sorted(arr)
    
    index = sorted_arr.index(item)
    
    percentile = (index + 1) / len(sorted_arr) * 100
    
    return percentile

for i in range(len(playerVals)):
    playerVals[i] = NHL_data.loc[NHL_data['player_name'] == player_name, playerStats[i]].values[0]
    Percentiles[i] = find_percentile(NHL_data[playerStats[i]], playerVals[i])

print('\n')
print(player_name,'\n: Goals For', playerVals[0],' League Percentile: ', Percentiles[0])
print('\n : Assists:', playerVals[1],' League Percentile: ', Percentiles[1])
print('\n : Primary Points:', playerVals[2],' League Percentile: ', Percentiles[2])
print('\n : Primary Assists:', playerVals[3],' League Percentile: ', Percentiles[3])
print('\n : XG For:', playerVals[4],' League Percentile: ', Percentiles[4])
print('\n : On Ice XG For:', playerVals[5],' League Percentile: ', Percentiles[5])
print('\n : On Ice Goals For:', playerVals[6],' League Percentile: ', Percentiles[6])
print('\n : On Ice XG Against:', playerVals[7],' League Percentile: ', Percentiles[7])
print('\n : On Ice Goals Against:', playerVals[8],' League Percentile: ', Percentiles[8])
print('\n : On Ice XG Percentage:', playerVals[9], '%', 'League Percentile: ', Percentiles[9])
print('\n : On Ice Goal Percentage:', playerVals[10],'%', 'League Percentile: ', Percentiles[10])
print('\n : Hits:', playerVals[11],' League Percentile: ', Percentiles[11])
print('\n : Blocked Shots:', playerVals[12],'League Percentile: ', Percentiles[12])
print('\n : Takeaways:', playerVals[13], 'League Percentile: ', Percentiles[13])
print('\n : Giveaways:', playerVals[14], 'League Percentile: ', 100 - Percentiles[14])
print('\n : Takeaways to Giveaways Ratio:', playerVals[15], 'League Percentile: ', Percentiles[15])
print('\n : Assist to Giveaways Ratio:', playerVals[16], 'League Percentile: ', Percentiles[16])
print('\n : Defensive Zone Giveaways:', playerVals[17], 'League Percentile: ', 100 - Percentiles[17])
print('\n : Neutral Zone Giveaways:', playerVals[18], 'League Percentile: ', 100 - Percentiles[18])
print('\n : Offensive Zone Giveaways:', playerVals[19], 'League Percentile: ', 100 - Percentiles[19])
print('\n : Defensive Zone Takeaways:', playerVals[20], 'League Percentile: ', Percentiles[20])
print('\n : Neutral Zone Takeaways:', playerVals[21], 'League Percentile: ', Percentiles[21])
print('\n : Offensive Zone Takeaways:', playerVals[22], 'League Percentile: ', Percentiles[22])





# plt.figure(figsize=(10, 6))
# plt.bar(playerStats, playerVals, color=['blue', 'green', 'red'])

# plt.text(0.5, 1.1, player_name, transform=ax.transAxes, fontsize=16, ha='center', weight='bold')
# plt.title(f'Statistics for {player_name}')
# plt.xlabel('Statistics')
# plt.ylabel('Value')
# plt.show()

