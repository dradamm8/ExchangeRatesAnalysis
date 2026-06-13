from database_connection.conn import *
from data_processing.data_utils import *
import sys



def main():
    
    data = get_data("2022-02-03", "2022-05-06") 
    
    print("Jestem tu")
    conn = make_sqlalchemy_connection()
    if not conn:
        print("Nie udalo sie polaczyc!")
        sys.exit(1)
    else:
        print("Polaczono!")

    
   # cur = conn.cursor()
    df_to_db(data, conn)

    #cur.close()
    conn.close()



if __name__ == "__main__":
    main()