# @version 0.2.8
greet: public(String[100])

@external
def __init__():
    # REF: https://www.youtube.com/watch?v=-kZpEmNnzyE
    # (blockchain-venv) C:\Code\blockchain-learning\src>vyper contracts\HelloWorld.vy << to compile
  self.greet = "Hello World"