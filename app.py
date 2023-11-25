from shiny import App, render, ui, reactive
from lineup_fd_generation import main

choices = ["NFL", "NBA"]

app_ui = ui.page_fluid(
    ui.panel_title("FanDuel Lineup Optimizer"),
    ui.input_numeric("n", "Salary Cap", value=60000),
    ui.input_selectize("league", "League", choices),
    ui.input_action_button("optimize", "Optimize"),
    ui.output_table("optimal_nfl_lineup"),
    ui.output_text("optimal_nba_lineup")
)


def server(input, output, session):
    @output
    @render.table
    @reactive.event(input.optimize)
    def optimal_nfl_lineup():
        if input.league() == "NFL":
            return main(input.n())
    
    @output
    @render.text
    @reactive.event(input.optimize)
    def optimal_nba_lineup():
        if input.league() == "NBA":
            return "NBA coming soon"


app = App(app_ui, server)
