from dash import Dash, html, dcc, Input, Output, callback
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from data_processing.data_utils import *
from database_connection.conn import *

def make_dashboard():
    app = Dash()

    fig = make_subplots(rows=2, cols=3, subplot_titles = title_codes)
        fig.update_layout(title = {'text': "Kursy walut"}, showlegend = False)
        
        fig2 = go.Figure()
        fig2.update_layout(title = {'text': "Wartości standaryzowane"})
        
        
        fig3 = go.Figure()
        fig3.update_layout(title = {'text': "Wartości procentowe względem 01.01.2022"})
        
        
        fig4 = make_subplots(rows=2, cols=3, subplot_titles = title_codes)
        fig4.update_layout(title = {'text': "Wartości z ostatnich 3 miesięcy i przewidywane (model ARIMA)"}, showlegend = False)


    app.layout = html.Div(children=[
        html.H1(children='Dashboard danych walutowych', style = {'text-align' : 'center', 'font-family' : 'Arial', 'font-weight' : "bold"}),
        
        dcc.Graph(
            id='subplots',
            figure=fig
        ),

        dcc.Graph(
            id='stand',
            figure=fig2
        ),

        dcc.Graph(
            id='perc',
            figure=fig3
        ),

        dcc.Graph(
            id='pred',
            figure=fig4
        ),

        dcc.Interval(
                id='interval-component',
                interval= 2*60*1000,
                n_intervals=0
            )
    ])

    @callback(Output("subplots", 'figure'),
            Output("stand", 'figure'),
            Output("perc", 'figure'),
            Output("pred", 'figure'),
            Input('interval-component','n_intervals')
    )
    def update_graph(n):
        df = get_data_from_db()
        df = get_data_from_db()
        model_dict = model_dict_from_pickle("arima")

        df_to_ml = prepare_data(df)
        df_dict = make_df_dict(df_to_ml)

        pred_dict = predict_data(df_dict, model_dict, "arima")
        
        df_scaled = (df - df.mean()) / df.std()
        df_perc = df / df.iloc[0] * 100
        
        inv_dict, inv_old_data_dict, inv_pred_dict = inv_transform(df_dict, pred_dict, df)

        title_codes = [*map(lambda x: x.upper() + '/PLN', codes)]
        colors = [('blue', 'lightblue'), ('red', 'lightcoral'), ('green', 'lightgreen'), ('purple', 'mediumpurple'), 
                ('darkorange', 'navajowhite'), ('deeppink', 'lightpink')]
        
        
        
        for code in codes:
            fig2.add_scatter(x = df_scaled.index, y = df_scaled[code], mode = "lines", name = code.upper())
            fig3.add_scatter(x = df_perc.index, y = df_perc[code], mode = "lines", name = code.upper())
            
        r_c = [(1,1), (1,2), (1,3), (2,1), (2,2), (2,3)]
        
        for rowcol, code, color in zip(r_c, codes, colors):
            
            row, col = rowcol
            c1, c2 = color
            
            fig.add_trace(go.Scatter(x=df.index, y=df[code].values, mode = "lines", line = dict(color = c1)), row = row, col = col)
        
            curr_pred = inv_pred_dict[code]
            old_data = inv_old_data_dict[code]
            old_data = old_data.iloc[-90:]
            
            curr_pred = pd.concat((old_data.iloc[[-1]], curr_pred), axis = 0)
        
            
            fig4.add_trace(go.Scatter(x = old_data.index, y = old_data[code], mode = "lines", line = {'color' : c1}), row = row, col = col)
            fig4.add_trace(go.Scatter(x = curr_pred.index, y = curr_pred[code], mode = "lines", line = {'color' : c2})
                        , row = row, col = col)


        return fig, fig2, fig3, fig4
    
if __name__ == '__main__':
    app.run(debug=True, port = 8000)