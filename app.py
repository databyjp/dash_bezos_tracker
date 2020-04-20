# ========== (c) JP Hwang 19/4/20  ==========

import logging

# ===== START LOGGER =====
logger = logging.getLogger(__name__)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
sh.setFormatter(formatter)
root_logger.addHandler(sh)

import pandas as pd
import requests
import plotly.express as px
import datetime
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from fredapi import Fred
import dash_bootstrap_components as dbc

desired_width = 320
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', desired_width)

# ========== LOAD TOKENS / SET CONSTANTS==========
with open('../../tokens/tiingo_token.txt', 'r') as f:
    tiingo_token = f.read().strip()
with open('../../tokens/fred_token.txt', 'r') as f:
    fred_token = f.read().strip()
fred = Fred(api_key=fred_token)
amzn_df_loc = 'amzn_df.csv'
umemp_df_loc = 'unemp_df.csv'
median_us_income = 33706  # https://fred.stlouisfed.org/series/MEPAINUSA672N
median_world_income = 2920  # https://news.gallup.com/poll/166211/worldwide-median-household-income-000.aspx


# ========== GET STOCK DATA ==========
def get_stock_data(tkn, sym='amzn', start_date='2020-01-01'):
    headers = {'Content-Type': 'application/json'}

    requestResponse = requests.get("https://api.tiingo.com/tiingo/daily/" + sym + "/prices?startDate=" + start_date + "&token=" + tkn, headers=headers)
    if requestResponse.status_code == 200:
        logger.info(f'Success fetching {sym} data from {start_date} to today')
    else:
        logger.warning(f'Something looks wrong - status code {requestResponse.status_code}')

    return requestResponse


# ========== GET BEZOS DATA ==========
def get_bezos_data():
    amzn_data = get_stock_data(tiingo_token).json()
    temp_df = pd.DataFrame(amzn_data)

    # CALCULATE BEZOS' NET WORTH
    temp_df = temp_df.assign(bezos_bucks=temp_df.close * 498 * 10**6 * 0.112)
    temp_df = temp_df.assign(bezos_year=(temp_df.close - temp_df.iloc[0].close) * 498 * 10**6 * 0.112)
    temp_df = temp_df.assign(bezos_week=[(row['close'] - temp_df.iloc[max(0, i-6)].close) * 498 * 10**6 * 0.112 for i, row in temp_df.iterrows()])
    return temp_df


def update_bezos_data(df_loc=amzn_df_loc):
    new_df = get_bezos_data()
    new_df.to_csv(df_loc)
    return new_df


# ========== PLOT AMAZON STOCK DATA ==========
# fig = px.scatter(amzn_df, x='date', y='close', template='ggplot2', title='AMZN stock price', labels={'close': 'Price (USD)', 'date': 'Date'})
# fig.update_traces(mode='lines+markers')
# fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])  # hide weekends
# fig.show()

# ========== CALCULATE BEZOS' NET WORTH ==========
# fig = px.scatter(amzn_df, x='date', y='bezos_year', template='ggplot2', title="Jeff Bezos' 2020 net worth gains",
#                  labels={'close': 'Change to Net Worth (USD)', 'date': 'Date', 'bezos_year': 'YTD gains'})
# fig.update_traces(mode='lines+markers')
# fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])  # hide weekends
# fig.show()

# bezos_df = amzn_df.melt(id_vars='date', value_vars=['bezos_bucks', 'bezos_year', 'bezos_week'])


# ========== GET THE LATEST WEEKLY UNEMPLOYMENT DATA ==========
def update_unemp_data(df_loc=umemp_df_loc):
    unemp_data = fred.get_series('ICSA')
    new_df = unemp_data.to_frame('unemployment').reset_index().rename(columns={'index': 'date'})
    new_df.to_csv(df_loc)
    return new_df

# fig = px.scatter(unemp_df, x='date', y='unemployment', log_y=True)
# fig.update_traces(mode='lines+markers')
# fig.show()

# ========== DASH APP ==========
amzn_df = update_bezos_data()
unemp_df = update_unemp_data()

theme_link = 'https://stackpath.bootstrapcdn.com/bootswatch/4.4.1/flatly/bootstrap.min.css'
app = dash.Dash(__name__, external_stylesheets=[theme_link])

server = app.server

title = 'Jeff Bezos Wealth | COVID-19 Economics tracker'
app.title = title
app.layout = dbc.Container([
    dbc.Jumbotron([
        html.H2(title),
        html.Hr(className="my-2"),
        html.P("Track Jeff Bezos' estimated fortunes and the overall economy's (not so) fortunes during this difficult time."),
        html.P('(For entertainment / web programming demonstration purposes only.)', className="text-muted"),
        dbc.Button(html.Small(html.A('Source Code', href='#', style={'color': 'white'})), color='primary'),
        ' ',
        dbc.Button(html.Small(html.A('Tutorial article', href='#', style={'color': 'white'})), color='primary'),
    ]),
    html.Div([
        html.Div(id='bezos_text', children=[]),
        dcc.Interval(
            id='bezos_text-interval',
            interval=1000,  # in milliseconds
            n_intervals=0
        )
    ]),
    html.Hr(className="my-2"),
    dbc.Alert([f"Here's the overall change to Jeff Bezos' net worth based on his estimated Amazon shares."], color="info"),
    html.Div([
        dcc.Graph(
            id='bezos-worth-graph',
            config={"displayModeBar": False}
        ),
        dcc.Interval(
            id='bezos-graph-interval',
            interval=60 * 60 * 1000,  # in milliseconds
            n_intervals=0
        )
    ]),
    # TODO - add unemployment graph for context
    html.Hr(className="my-2"),
    dbc.Alert(["At the same time, weekly filings for unemployment in the United States has exploded, starting in March 2020."], color="info"),
    html.Div([
        dcc.Graph(
            id='unemp-graph',
            config={"displayModeBar": False}
        ),
        dcc.Interval(
            id='unemp-interval',
            interval=60 * 60 * 1000,  # in milliseconds
            n_intervals=0
        )
    ]),
    # TODO - add notes about me / link to blog
])


@app.callback(Output('bezos-worth-graph', 'figure'),
              [Input('bezos-graph-interval', 'n_intervals')])
def update_bezos_graph(n):
    tmp_amzn_df = update_bezos_data()
    fig = px.scatter(tmp_amzn_df, x='date', y='bezos_year', template='ggplot2', title="Jeff Bezos' 2020 net worth gains",
                     labels={'close': 'Change to Net Worth (USD)', 'date': 'Date', 'bezos_year': 'YTD gains'}, height=350)
    fig.update_traces(mode='lines+markers')
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])  # hide weekends

    return fig


@app.callback(Output('unemp-graph', 'figure'),
              [Input('bezos-graph-interval', 'n_intervals')])
def update_unemp_graph(n):
    unemp_df = update_unemp_data()
    fig = px.scatter(unemp_df, x='date', y='unemployment', template='plotly_white', title="Weekly new unemployment filings - U.S.",
                     labels={'close': 'Unemployment filings', 'date': 'Date', 'unemployment': 'Weekly Filings'}, log_y=True, height=350)
    fig.update_traces(mode='lines+markers')

    return fig


@app.callback(Output('bezos_text', 'children'),
              [Input('bezos_text-interval', 'n_intervals')])
def update_bezos_text(n):
    ytd_td = datetime.datetime.now() - datetime.datetime.fromisoformat('2020-01-01')
    ytd_seconds = ytd_td.total_seconds()
    bezos_secondly = round(amzn_df.iloc[-1].bezos_year / ytd_seconds)
    bezos_tot = bezos_secondly * n
    unemp_secondly = round(sum(unemp_df.unemployment[-3:]) / (3 * 7 * 24 * 60 * 60), 1)

    bezos_txt = [dbc.Alert([f'Hi, you have been on this page for ', dbc.Badge(f'{n} seconds', color="primary", className="mr-1"), '. In that time:'], color="info")]

    card_content_worth = [
        dbc.CardHeader(f"Bezos' net worth has increased by: "),
        dbc.CardBody([
            html.H3([dbc.Badge(f"US${int(bezos_secondly * n)}", color='success')], className="card-title"),
            html.P([
                f"That is ", dbc.Badge(str(round(bezos_tot/median_us_income, 1)), color='primary'),
                " typical U.S. incomes' worth of money."],
                className="card-text",
            ),
        ])]

    card_content_unemp = [
        dbc.CardHeader(f"Meanwhile, just in the U.S.:"),
        dbc.CardBody([
            html.H5([dbc.Badge(f"{int(unemp_secondly * n)}", color='danger'), " unemployment filings were made"], className="card-title"),
            html.P(
                f"{round(sum(unemp_df.unemployment[-3:])/10**6, 1)} million people filed for unemployment in the U.S. in the last 3 weeks. ",
                className="card-text",
            ),
        ])]

    card_content_inc_stats = dbc.CardBody(
        [
            html.Blockquote(
                [
                    html.P(html.Small(f"The typical (median) per-person income is:"), className="text-muted"),
                    html.P(f"US${median_world_income} world-wide, and US${median_us_income} in the United States."),
                    html.Footer(
                        html.Small(['Stats: ', html.A("U.S.", href="https://fred.stlouisfed.org/series/MEPAINUSA672N"), ', ', html.A("World", href="https://news.gallup.com/poll/166211/worldwide-median-household-income-000.aspx")]),
                    ),
                ],
                className="blockquote",
            )
        ]
    )

    card_content_unemp_stats = dbc.CardBody(
        [
            html.Blockquote(
                [
                    html.P(html.Small(f"Typically, 1 to 1.2 million people file for unemployment benefits every month in the United States."), className="text-muted"),
                    html.P(f"The current figure ({round(sum(unemp_df.unemployment[-3:])/10**6, 1)} million in 3 weeks) is about {round(sum(unemp_df.unemployment[-3:])/(0.9*10**6), 1)} times the normal and unprecedented."),
                    html.Footer(
                        html.Small([html.A("Source", href="https://fred.stlouisfed.org/series/ICSA")]),
                    ),
                ],
                className="blockquote",
            )
        ]
    )

    cards = dbc.CardColumns([
        dbc.Card(card_content_worth, color="success", outline=True),
        dbc.Card(card_content_inc_stats, color="secondary", outline=True),
        dbc.Card(card_content_unemp, color="danger", outline=True),
        dbc.Card(card_content_unemp_stats, color="warning", outline=True),
    ])

    bezos_txt.append(cards)

    return bezos_txt


if __name__ == '__main__':
    app.run_server(debug=False)
