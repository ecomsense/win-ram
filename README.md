
# Win-Ram


## Install python 3.9 for windows from the below list. 
Adjust suitably for your windows operating system. Usually you need to install 64-bit version recommended [python 3.9.13](https://www.python.org/downloads/release/python-3913/)

## Install Git Bash. 
This is [enhanced terminal plus git](), so that you can seamlessly update your system with the latest changes uploaded to github

## Start the bash terminal 
create necessary directories and cd to `E:\py`

## install the virtualenv
Virtualenv helps to have a self contained application with python. This way it will not mess with your operating system.
`python -m venv venv`

## cd to the newly created virtualenv from  `E:\py`
`cd venv`

## Activate the environment, from within the venv directory
`. Scripts/activate`


## Now lets download our app and cd to the our application directory that contains main.py file 
```
git clone https://github.com/pannet1/win-ram.git
cd win-ram/dealer_web
```
## Install the required libraries for our application to work smoothly
`pip install -r ../requirements.txt`

## Configuration
Provide the list of users in the credential file `py\ram_win.yml` file.

## Run the application
`python main.py`

## Shortcuts
you can link the bat files found inside win-ram directory and use it to run the `main.py` or `update.bat` to get the latest version of the win-ram from github without messing in the terminal.

Happy trading !
```
