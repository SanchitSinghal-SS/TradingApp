import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
# Function to calculate EMA


def calculate_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()


# Load EQUITY_COPY.csv to get the list of tickers

equity_df = pd.read_csv(
    'data\EQUITY_L copy.csv')
# Streamlit app
st.title('Nifty Equity Shares Analysis')

# Dropdown to select ticker
ticker = st.selectbox('Select a ticker:', equity_df['SYMBOL'])

# Load the historical data for the selected ticker
if ticker:
    print("Outside download try catch block")
    try:
        data = yf.download(f"{ticker}.NS")
        data.to_csv(
            f"data\\HistoricalData\\{ticker}.csv")
        print(f"Downloaded {ticker} data")
    except:
        print("Cannot download data")

    historical_data_path = f'data/HistoricalData/{ticker}.csv'
    try:
        df = pd.read_csv(historical_data_path, parse_dates=[
                         'Date'], index_col='Date')

        # Get date range for the data
        min_date = df.index.min()
        max_date = df.index.max()

        # Date inputs for filtering
        start_date = st.date_input(
            'Start date', min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input('End date', max_date,
                                 min_value=min_date, max_value=max_date)

        if start_date > end_date:
            st.error('Error: End date must fall after start date.')
        else:
            # Calculate EMAs for the entire dataset
            df['EMA_5'] = calculate_ema(df['Close'], 5)
            df['EMA_13'] = calculate_ema(df['Close'], 13)
            df['EMA_26'] = calculate_ema(df['Close'], 26)

            # Filter data based on the selected date range
            filtered_df = df.loc[start_date:end_date]

            # Variables to track buy entries, sell signals, and individual trades
            buy_entries = []
            sell_entries_phase1 = []
            sell_entries_phase2 = []
            trades = []

            # Track each trade, buy 100 shares per buy entry
            trade_id = 0
            for i in range(1, len(filtered_df)):
                # Buy signals
                if (
                    (filtered_df['EMA_5'].iloc[i] > filtered_df['EMA_13'].iloc[i] and filtered_df['EMA_5'].iloc[i-1] < filtered_df['EMA_13'].iloc[i-1]) or
                    (filtered_df['EMA_5'].iloc[i] > filtered_df['EMA_26'].iloc[i]
                     and filtered_df['EMA_5'].iloc[i-1] < filtered_df['EMA_26'].iloc[i-1])
                ) and \
                    (filtered_df['Close'].iloc[i] > filtered_df['Close'].iloc[i-1]) and \
                        (filtered_df['Volume'].iloc[i] > filtered_df['Volume'].iloc[i-1]) and (filtered_df['Close'].iloc[i] > filtered_df['Open'].iloc[i]):

                    # Record the buy entry and create a new trade
                    buy_entry = filtered_df.iloc[i]
                    buy_entries.append(buy_entry)
                    trades.append({
                        'id': trade_id,
                        'buy_date': buy_entry.name,
                        'buy_price': buy_entry['Close'],
                        'shares': 100,
                        'sell_dates': [],
                        'sell_prices': [],
                        'profit': 0,
                        'status': 'open'
                    })
                    trade_id += 1

                # Sell signals for Phase 1
                elif (
                    (filtered_df['EMA_5'].iloc[i] < filtered_df['EMA_13'].iloc[i] and filtered_df['EMA_5'].iloc[i-1] > filtered_df['EMA_13'].iloc[i-1]) or
                    (filtered_df['EMA_5'].iloc[i] < filtered_df['EMA_26'].iloc[i]
                     and filtered_df['EMA_5'].iloc[i-1] > filtered_df['EMA_26'].iloc[i-1])
                ):
                    sell_entry = filtered_df.iloc[i]
                    sell_entries_phase1.append(sell_entry)

                    # Partial sell 25%
                    for trade in trades:
                        if trade['status'] == 'open' and trade['shares'] > 0:
                            shares_to_sell = min(
                                trade['shares'], 25)  # 25% sell
                            profit = shares_to_sell * \
                                (sell_entry['Close'] - trade['buy_price'])
                            trade['shares'] -= shares_to_sell
                            trade['profit'] += profit
                            trade['sell_dates'].append(sell_entry.name)
                            trade['sell_prices'].append(sell_entry['Close'])
                            if trade['shares'] == 0:
                                trade['status'] = 'closed'

                # Sell signals for Phase 2 (close entire trade)
                elif (
                    filtered_df['EMA_13'].iloc[i] < filtered_df['EMA_26'].iloc[i] and filtered_df['EMA_13'].iloc[i -
                                                                                                                 1] > filtered_df['EMA_26'].iloc[i-1]
                ):
                    sell_entry = filtered_df.iloc[i]
                    sell_entries_phase2.append(sell_entry)

                    # Close the remaining position
                    for trade in trades:
                        if trade['status'] == 'open' and trade['shares'] > 0:
                            # Close all remaining shares
                            shares_to_sell = trade['shares']
                            profit = shares_to_sell * \
                                (sell_entry['Close'] - trade['buy_price'])
                            trade['shares'] = 0
                            trade['profit'] += profit
                            trade['sell_dates'].append(sell_entry.name)
                            trade['sell_prices'].append(sell_entry['Close'])
                            trade['status'] = 'closed'

            # Summary of all trades
            st.subheader("All Trades Summary")
            trade_summary = []
            for trade in trades:
                trade_summary.append({
                    'Trade ID': trade['id'],
                    'Buy Date': trade['buy_date'],
                    'Buy Price': trade['buy_price'],
                    'Sell Dates': trade['sell_dates'],
                    'Sell Prices': trade['sell_prices'],
                    'Profit': trade['profit'],
                    'Status': trade['status']
                })

            trade_df = pd.DataFrame(trade_summary)
            st.dataframe(trade_df)

            # Total Profit/Loss
            total_profit = sum([trade['profit'] for trade in trades])
            st.write(f"Total profit/loss for the period: {total_profit:.2f}")

            # Dropdown to select individual trade for detailed graph
            trade_id_to_view = st.selectbox("Select a trade to view details:", [
                                            trade['id'] for trade in trades])

            # Display detailed graph for the selected trade
            if trade_id_to_view is not None:
                selected_trade = [
                    trade for trade in trades if trade['id'] == trade_id_to_view][0]

                fig = go.Figure(data=[go.Candlestick(x=filtered_df.index,
                                                     open=filtered_df['Open'],
                                                     high=filtered_df['High'],
                                                     low=filtered_df['Low'],
                                                     close=filtered_df['Close'],
                                                     increasing_line_color='green',
                                                     decreasing_line_color='red')])

                # Add Buy and Sell signals for the selected trade
                fig.add_trace(go.Scatter(
                    x=[selected_trade['buy_date']], y=[selected_trade['buy_price']], mode='markers', name='Buy Signal',
                    marker=dict(color='yellow', size=10, symbol='triangle-up')))
                fig.add_trace(go.Scatter(
                    x=selected_trade['sell_dates'], y=selected_trade['sell_prices'], mode='markers', name='Sell Signal',
                    marker=dict(color='white', size=10, symbol='triangle-down')))

                # Update layout
                fig.update_layout(
                    title=f'Trade Details for Trade ID {selected_trade["id"]}',
                    xaxis_title='Date',
                    yaxis_title='Price',
                    xaxis_rangeslider_visible=False
                )

                st.plotly_chart(fig)

    except FileNotFoundError:
        st.error(f"Data for ticker {
                 ticker} not found in 'historical_data' folder.")
