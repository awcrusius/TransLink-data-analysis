from etl_helper import *
def test_switch():
    switch = 'Transit'

def main():
    # Create full url from config.yaml
    with open('config/config.yaml', 'r') as file:
        config = yaml.load(file,Loader=yaml.SafeLoader)
    
    # Add api keys to config in memory only
    load_api_keys(config)

    print("num keys: ", config["Translink"]["num_keys"])
    
    
if __name__=='__main__':
    main()