from database_connection.conn import *
from data_processing.data_utils import *
from ml.ml_utils import *
import sys
import warnings
warnings.simplefilter(action='ignore')
from dashboards.dashboards import *

# mam już wszystko jeśli chodzi o pobieranie i zapisywanie danych i modeli
# teraz - dashboardy

def main():
    
    load_dotenv()
    
    make_dashboard()

if __name__ == "__main__":
    main()