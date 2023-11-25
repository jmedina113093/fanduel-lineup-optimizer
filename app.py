import pandas as pd
import numpy as np
from shiny import App, render, ui, reactive
from lineup_fd_generation import main_nfl, main_nba, main_mlb

choices = ["NFL", "NBA", "MLB"]

app_ui = ui.page_fluid(
    ui.panel_title("FanDuel Lineup Optimizer"),
    ui.input_numeric("n", "Salary Cap", value=60000),
    ui.input_selectize("league", "League", choices),
    ui.input_action_button("optimize", "Optimize"),
    ui.output_table("optimal_nfl_lineup_table"),
    ui.output_table("optimal_nba_lineup_table"),
    ui.output_text("optimal_nfl_lineup_text"),
    ui.output_text("optimal_nba_lineup_text"),
    ui.output_text("optimal_mlb_lineup_text")
)


def server(input, output, session):
    @output
    @render.table
    @reactive.event(input.optimize)
    def optimal_nfl_lineup_table():
        if input.league() == "NFL":
            return main_nfl(input.n())

    @output
    @render.table
    @reactive.event(input.optimize)
    def optimal_nba_lineup_table():
        if input.league() == "NBA":
            return main_nba(input.n())
    
    @output
    @render.text
    @reactive.event(input.optimize)
    def optimal_nfl_lineup_text():
        if (len(main_nfl(input.n())) == 0) and (input.league() == "NFL"):
            return "There are no NFL games today to generate a FanDuel Daily Fantasy Lineup"

    @output
    @render.text
    @reactive.event(input.optimize)
    def optimal_nba_lineup_text():
        if (len(main_nba(input.n())) == 0) and (input.league() == "NBA"):
            return "There are no NBA games today to generate a FanDuel Daily Fantasy Lineup"
        
    @output
    @render.text
    @reactive.event(input.optimize)
    def optimal_mlb_lineup_text():
        if input.league() == "MLB":
            return main_mlb()


app = App(app_ui, server)
