import bs4 as bs
import urllib.request
import pandas as pd
import numpy as np
import pulp

def scrape_dfs_table(url):
    #initialize list for dataframe
    df_list = []

    #specifies source website
    source = urllib.request.urlopen(url).read()
    soup = bs.BeautifulSoup(source, 'lxml')

    #scrapes specific table from website and appends data to list
    tbody = soup.find('table', class_='stat-table').find_all('tr')
    for i, row in enumerate(tbody):
        if i == 0:
            pass
        else:
            cols = row.findChildren(recursive=False)
            cols = [ele.text.strip() for ele in cols]
            df_list.append(cols)
    
    return pd.DataFrame(df_list[1:], columns=df_list[0])

def main(salary):
    # load dfs salaries for positions and defenses, then concatenate
    df_positions = scrape_dfs_table('https://www.numberfire.com/nfl/daily-fantasy/daily-football-projections')[['Player', 'FP', 'Salary', 'Value']]
    df_defense = scrape_dfs_table('https://www.numberfire.com/nfl/daily-fantasy/daily-football-projections/D')[['Player', 'FP', 'Salary', 'Value']]
    df = pd.concat([df_positions, df_defense])

    #extract player name, position, and team from data
    df['Player_Name'] = df['Player'].str.extract(r'(.*?)\t')
    df['Player_Position'] = df['Player'].str.extract(r'\n(QB|RB|WR|TE|K|D/ST)\n')
    df['Player_Position'] = np.where(df['Player_Name'].str.contains('D/ST'), 'DEF', df['Player_Position'])
    df['Player_Team'] = df['Player'].str.extract(r'@\xa0(.*?)\n')

    #turn values into float
    df['Salary'] = df['Salary'].replace('[\$,]', '', regex=True).astype('float')
    df['FP'] = df['FP'].astype('float')

    #drop unnecessary columns
    df = df[['Player_Name', 'Player_Position', 'Player_Team', 'FP', 'Salary', 'Value']]

    salary_cap = salary

    # Create a linear programming problem
    prob = pulp.LpProblem("FantasyTeamOptimization", pulp.LpMaximize)

    # Create binary variables for player selection
    #selected_players = pulp.LpVariable.dicts("PlayerSelected", df['Player_Name'], cat=pulp.LpBinary)

    players = len(df)
    selected_players = pulp.LpVariable.dicts("PlayerSelected", range(players), cat="Binary")

    # Objective function: maximize total points
    prob += pulp.lpSum(df['FP'].iloc[i] * selected_players[i] for i in range(players))

    # Salary constraint
    prob += pulp.lpSum(df['Salary'].iloc[i] * selected_players[i] for i in range(players)) <= salary_cap

    # one QB
    prob += pulp.lpSum(selected_players[i] for i in range(players) if df['Player_Position'].iloc[i] == 'QB') == 1

    # at most 3 rb
    prob += pulp.lpSum(selected_players[i] for i in range(players) if df['Player_Position'].iloc[i] == 'RB') <= 3

    # at most 3 rb
    prob += pulp.lpSum(selected_players[i] for i in range(players) if df['Player_Position'].iloc[i] == 'RB') >= 2

    # at most 3 wr
    prob += pulp.lpSum(selected_players[i] for i in range(players) if df['Player_Position'].iloc[i] == 'WR') <= 4

    # at most 3 wr
    prob += pulp.lpSum(selected_players[i] for i in range(players) if df['Player_Position'].iloc[i] == 'WR') >= 3

    # at most 5 rb and wr
    prob += pulp.lpSum(selected_players[i] for i in range(players) if (df['Player_Position'].iloc[i] == 'RB') or (df['Player_Position'].iloc[i] == 'WR')) <= 6

    # one TE
    prob += pulp.lpSum(selected_players[i] for i in range(players) if df['Player_Position'].iloc[i] == 'TE') == 1

    # one DEF
    prob += pulp.lpSum(selected_players[i] for i in range(players) if df['Player_Position'].iloc[i] == 'DEF') == 1

    # Solve the problem
    prob.solve()
    
    lineup_df = pd.DataFrame(columns = df.columns)

    for i in range(players):
        if selected_players[i].varValue == 1:
            lineup_df = pd.concat([lineup_df, df.iloc[i:i+1]])
    
    lineup_df['position_sort'] = pd.Categorical(lineup_df['Player_Position'], ["QB", "RB", "WR", "TE", "DEF"])
    lineup_df = lineup_df.sort_values("position_sort")

    return lineup_df.loc[:, ['Player_Name', 'Player_Position', 'Player_Team', 'FP', 'Salary']]
