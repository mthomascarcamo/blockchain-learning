# @version 0.2.11
greet: public(String[100])

@external
def __init__():
    # REF: https://www.youtube.com/watch?v=-kZpEmNnzyE
    # (blockchain-venv)  vyper blockchain_learning/src/contracts/HelloWorld.vy << to compile
  self.greet = "Hello World"