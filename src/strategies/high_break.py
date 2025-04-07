from toolkit.kokoo import blink


class HighBreak:
    def __init__(self):
        self.__name__ = "high break"
        print(self.__name__)

    def run(self):
        while True:
            print("run")
            blink()
