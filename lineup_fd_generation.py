import bs4 as bs
import urllib.request
import pandas as pd
import numpy as np
import pulp

def scrape_dfs_table(url):
    """
    scrapes url and returns table as a dataframe, using the second row as headers
    """
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


def clean_salary_and_fp(df):
    """
    cleans the salary and FP columns of df by returning as float
    """
    df['Salary'] = df['Salary'].replace('[\$,]', '', regex=True).astype('float')
    df['FP'] = df['FP'].astype('float')
    return df


def initialize_pulp(df, salary_cap):
    """
    initializes pulp maximize optimization problem
    returns the problem, player variables, and selected player variables
    also adds optimization function of maximizing projected points to the problem,
    and adds the constraint the total salary must be under the salary cap
    """
    # Create a linear programming problem
    prob = pulp.LpProblem("FantasyTeamOptimization", pulp.LpMaximize)

    # Initialize player variables
    players = len(df)
    selected_players = pulp.LpVariable.dicts("PlayerSelected", range(players), cat="Binary")

    # Objective function: maximize total points
    prob += pulp.lpSum(df['FP'].iloc[i] * selected_players[i] for i in range(players))

    # Salary constraint
    prob += pulp.lpSum(df['Salary'].iloc[i] * selected_players[i] for i in range(players)) <= salary_cap

    return prob, players, selected_players


def return_optimal_lineup_df(df, players, selected_players, position_col_name, position_sort_list):
    """
    returns a df of the selected, optimized lineup, sorted by designated position order
    """

    lineup_df = pd.DataFrame(columns = df.columns)

    for i in range(players):
        if selected_players[i].varValue == 1:
            lineup_df = pd.concat([lineup_df, df.iloc[i:i+1]])
    
    lineup_df['position_sort'] = pd.Categorical(lineup_df[position_col_name], position_sort_list)
    return lineup_df.sort_values("position_sort")


def main_nfl(salary_cap):
    """
    returns a df of the optimal NFL lineup for FanDuel Daily Fantasy Sports
    """
    # load dfs salaries and projections for positions and defenses, then concatenate
    df_positions = scrape_dfs_table('https://www.numberfire.com/nfl/daily-fantasy/daily-football-projections')[['Player', 'FP', 'Salary', 'Value']]
    df_defense = scrape_dfs_table('https://www.numberfire.com/nfl/daily-fantasy/daily-football-projections/D')[['Player', 'FP', 'Salary', 'Value']]
    df = pd.concat([df_positions, df_defense])

    #extract player name, position, and team from data
    df['Player_Name'] = df['Player'].str.extract(r'(.*?)\t')
    df['Player_Position'] = df['Player'].str.extract(r'\n(QB|RB|WR|TE|K|D/ST)\n')
    df['Player_Position'] = np.where(df['Player_Name'].str.contains('D/ST'), 'DEF', df['Player_Position'])
    df['Player_Team'] = df['Player'].str.extract(r'@\xa0(.*?)\n')

    # turn salary and fp into floats, and drop unnecessary columns
    df = clean_salary_and_fp(df)[['Player_Name', 'Player_Position', 'Player_Team', 'FP', 'Salary', 'Value']]

    # create linear programming problem, initialize player variables, define objective function and salary cap constraint
    prob, players, selected_players = initialize_pulp(df, salary_cap)

    #league-specific constraints

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

    # Store optimal lineup
    lineup_df = return_optimal_lineup_df(df, players, selected_players, position_col_name='Player_Position', position_sort_list=["QB", "RB", "WR", "TE", "DEF"])
    
    return lineup_df.loc[:, ['Player_Name', 'Player_Position', 'Player_Team', 'FP', 'Salary']]


def main_nba(salary_cap):
    """
    returns a df of the optimal NBA lineup for FanDuel Daily Fantasy Sports
    """
    # load dfs salaries and projections
    df = scrape_dfs_table('https://www.numberfire.com/nba/daily-fantasy/daily-football-projections')[['Player', 'FP', 'Salary', 'Value']]

    # Extract Player Name and Position
    df['Player_Name'] = df['Player'].str.extract(r'(.*?)\n')
    df['Player_Position_Single'] = df['Player'].str.extract(r'\n(PG|SG|SF|PF|C)\n')
    df['Player_Position_Multiple'] = df['Player'].str.extract(r'\n(.*?/.*?)\n')
    df['Player_Position_Primary'] = df['Player_Position_Multiple'].str.extract(r'(.*?)/')
    df['Player_Position_Primary'] = np.where(df['Player_Position_Primary'].isna(),df['Player_Position_Single'],df['Player_Position_Primary'])
    df['Player_Position_Secondary'] = df['Player_Position_Multiple'].str.extract(r'/(.*)')

    # turn salary and fp into floats, and drop unnecessary columns
    df = clean_salary_and_fp(df)[['Player_Name', 'Player_Position_Primary', 'Player_Position_Secondary', 'FP', 'Salary', 'Value']]

    # create linear programming problem, initialize player variables, define objective function and salary cap constraint
    prob, players, selected_players = initialize_pulp(df, salary_cap)

    # NBA-specific constraints

    # two PG
    prob += pulp.lpSum(selected_players[i] for i in range(players) if (df['Player_Position_Primary'].iloc[i] == 'PG') or (df['Player_Position_Secondary'].iloc[i] == 'PG')) == 2

    # two SG
    prob += pulp.lpSum(selected_players[i] for i in range(players) if (df['Player_Position_Primary'].iloc[i] == 'SG') or (df['Player_Position_Secondary'].iloc[i] == 'SG')) == 2

    # two SF
    prob += pulp.lpSum(selected_players[i] for i in range(players) if (df['Player_Position_Primary'].iloc[i] == 'SF') or (df['Player_Position_Secondary'].iloc[i] == 'SF')) == 2

    # two PF
    prob += pulp.lpSum(selected_players[i] for i in range(players) if (df['Player_Position_Primary'].iloc[i] == 'PF') or (df['Player_Position_Secondary'].iloc[i] == 'PF')) == 2

    # one C
    prob += pulp.lpSum(selected_players[i] for i in range(players) if (df['Player_Position_Primary'].iloc[i] == 'C') or (df['Player_Position_Secondary'].iloc[i] == 'C')) == 1

    # team of 9
    prob += pulp.lpSum(selected_players[i] for i in range(players)) == 9

    # Solve the problem
    prob.solve()
    
    # Store optimal lineup
    lineup_df = return_optimal_lineup_df(df, players, selected_players, position_col_name='Player_Position_Primary', position_sort_list=["PG", "SG", "SF", "PF", "C"])

    return lineup_df.loc[:, ['Player_Name', 'Player_Position_Primary', 'Player_Position_Secondary', 'FP', 'Salary']]
    

def main_mlb():
    return "MLB coming soon..."