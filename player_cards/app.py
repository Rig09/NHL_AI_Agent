import pandas as pd
from flask import Flask, request, render_template, jsonify
from player_card_stats import get_player_card_dict

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_player_names', methods=['GET'])
def get_player_names():
    # TODO: Need to tweak this for playoffs vs reg and multiple seasons
    skater_data = pd.read_csv("../data/skaters_regular_2023-2024.csv")
    player_names = skater_data["name"].unique().tolist()  # Get unique player names
    player_names.sort() # Alphabetical order
    return jsonify(player_names)


@app.route('/get_player_data', methods=['POST'])
def get_player_data():
    player_name = request.form['player_name']
    use_playoffs = 1 if 'use_playoffs' in request.form else 0

    # Get player data
    player_data = get_player_card_dict(player_name, use_playoffs)
    
    # Create a response dictionary containing both totals and percentiles
    data = {stat: {"total": value[0], "percentile": value[1]} for stat, value in player_data.items()}
    
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)