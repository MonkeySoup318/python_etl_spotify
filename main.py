import requests
import pandas as pd
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime
import datetime
import sqlite3


DATABASE_LOCATION = "sqlite:///my_played_tracks.sqlite"
USER_ID = "MonkeySoup"
TOKEN = "BQDDoe1y1ZPTncYEVg7KAHRNAotn5kL_shzW8jt4PdZuGTsEBUxKhlzIkoefwtKeoROtvOmZ9A41DyGBb-YggvKWQA_aGBwchTvPZuSHkM5wAm8GSRykkykMRBtYHtpw9mTAq6BeBTXprD9fCpJ8dYw_Biy8bZfQTf3Zev8tnU4bB_oFADnUrAV0gIrB_91_4zJjLx8Alw" # your Spotify API token

# Generate your Spotify API token here: https://developer.spotify.com/console/get-recently-played/
# Note: You need a valid Spotify account


def check_if_valid_data(df: pd.DataFrame) -> bool:
    # Check if DataFrame is empty
    if df.empty:
        print("No songs downloaded. Finishing execution of program")
        return False

    # Primary Key Check
    # Note: In this case I will use the 'played_at' series as Primary Key as you cannot simultaniously listen to two songs in Spotify
    if pd.Series(df['played_at']).is_unique:
        pass
    else:
        raise Exception('Primary Key Check is violated')

    # Check for NULL values
    if df.isnull().values.any():
        raise Exception('Null values detected in DataFrame')

    # Check that all timestamps are of yesterday's date
    yesterday = datetime.datetime.now() - datetime.timedelta(days = 1)
    yesterday = yesterday.replace(hour = 0, minute = 0, second = 0, microsecond = 0)

    timestamps = df["timestamp"].tolist()
    for timestamp in timestamps:
        if datetime.datetime.strptime(timestamp, '%Y-%m-%d') != yesterday:
            raise Exception('At least one of the returned songs does not come from within the last 24 hours')
    
    return True


if __name__ == '__main__':
    
    # This is the Extract part of the ETL process  

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {token}'.format(token = TOKEN)      
    }

    # Convert time to Unix timestamp in miliseconds
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days = 1)
    yesterday_unix_timestamp = int(yesterday.timestamp()) * 1000

    # Download all songs you've listened to "after yesterday", which means in the last 24 hours
    r = requests.get("https://api.spotify.com/v1/me/player/recently-played?after={time}".format(time = yesterday_unix_timestamp), headers = headers)

    data = r.json()
    print(data)
    
    song_names = []
    artist_names = []
    played_at_list = []
    timestamps = []

    # Extracting only the relevant bits of data from the json object      
    for song in data['items']:
        song_names.append(song['track']['name'])
        artist_names.append(song['track']['album']['artists'][0]['name'])
        played_at_list.append(song['played_at'])
        timestamps.append(song['played_at'][0:10])
    

    # Prepare a dictionary in order to turn it into a pandas dataframe below       
    song_dict = {
        'song_name' : song_names,
        'artist_name' : artist_names,
        'played_at' : played_at_list,
        'timestamp' : timestamps
        }
    
    song_df = pd.DataFrame(song_dict, columns = ['song_name', 'artist_name', 'played_at', 'timestamp'])
    #print(song_df)

    # Validate
    if check_if_valid_data(song_df):
        print('Data valid, proceed to Load stage')

    # Load
    engine = sqlalchemy.create_engine(DATABASE_LOCATION)
    conn = sqlite3.connect('my_played_tracks.sqlite')
    cursor = conn.cursor()

    sql_query = """
    CREATE TABLE IF NOT EXISTS my_played_tracks(
        song_name VARCHAR(200)
        , artist_name VARCHAR (200)
        , played_at VARCHAR (200)
        , timestamp VARCHAR (200)
        , CONSTRAINT primary_key_constraint PRIMARY KEY (played_at)
    )
    """

    cursor.execute(sql_query)
    print('Opened database succesfully')

    try:
        song_df.to_sql('my_played_tracks', engine, index = False, if_exists = 'append')
    except:
        print('Data already exists in the database')

    conn.close()
    print('Closed database succesfully')