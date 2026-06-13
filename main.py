from database_connection.conn import *
from data_processing.data_utils import *
import sys



def main():
    
    data = get_data("2022-01-01", "2025-05-06") 
        
    df_to_db(data)




if __name__ == "__main__":
    main()