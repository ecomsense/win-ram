### PRE-REQUISITES

- we recommend python 3.9+ but not greater than 3.9.
- git to clone this repository

### SETUP

- create a folder of your choice probably `gtt`. We will call this our root folder.

`cd` to this folder.

`git clone git+https://gitlab.com/pannet12/high-break`

`cd` to the now cloned folder `high-break`

- install from the `requirements.txt` file in this folder after ensuring python is in this path

`python -m pip install -r requirements.txt`

### FIRST RUN

when you run the program `main.py` like so ..

`python main.py`

for the first few times it will ...

- create a `data` folder inside this folder.
- it will download the trading symbols to `NFO.json`
- it will copy the `settings.yml` file from the `factory` folder into `data` folder we created above
  you please change the values appropriately in `settings.yml` located in the `data` folder only.  
  the `instrument_token` for the particular trading symbol will be available in the
  `NFO.json` file which we downloaded above.
- it will create an empty config file in the root folder.

```
#break_high.yml

app_key: "55105006cf3119906603c9d3ed937fc0"
user_id: "FA123456789"
password: "Ya@123456789"
imei: "abc1234"
vendor_code: "FA123456789_U"
pin: "O2Q5675T5I4GOOXCDOG7E3LNA5P65V5R"
```

### NORMAL WORKFLOW

After a successful run you just need to change the `settings.yml` in the
data folder for the correct trading_symbol and copy it instrument_token from
the `NFO.json`
