import pandas as pd
from flask import Flask, request, render_template, jsonify
from player_card_stats import get_player_card_dict

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_player_names', methods=['GET'])
def get_player_names():
    season = request.args.get('season', '2023')  # Default to 2023
    season_type = request.args.get('type', 'regular')
    file_path = f"../data/skaters/{season}/skaters_{season_type}_{season}.csv"

    try:
        skater_data = pd.read_csv(file_path)
    except FileNotFoundError:
        return jsonify([])

    player_names = skater_data["name"].unique().tolist()
    player_names.sort()
    return jsonify(player_names)

@app.route('/get_player_data', methods=['POST'])
def get_player_data():
    player_name = request.form['player_name']
    season = request.form['season']
    season_type = request.form['type']  # 'regular' or 'playoffs'

    # Get player data based on season and type
    player_data = get_player_card_dict(player_name, season, season_type)

    # Create a response dictionary containing both totals and percentiles
    data = {stat: {"total": value[0], "percentile": value[1]} for stat, value in player_data.items()}
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
