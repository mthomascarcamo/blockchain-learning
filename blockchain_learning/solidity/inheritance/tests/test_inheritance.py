#!/usr/bin/python3
# TODO: setup should allow removal of money
# NOTE: more familiar with unittest, os using that for now

import unittest
from brownie import Inheritance, accounts, reverts





class TestInheritanceContract(unittest.TestCase):

    initial_balance = 100

    def setUp(self):
        super().setUp()
        self.ancestor = accounts[0]
        self.heirs = accounts[1:]
        self.inheritance_contract = Inheritance.deploy({'from': self.ancestor, "value": self.initial_balance})

    def _deploy_without_funds(func):
        """Sets the contract up so that it's initalized with no money
        the tests are otherwise set up so that the contract is initialized with self.initial_balance"""
        def wrapper(self):
            self.inheritance_contract = Inheritance.deploy(
                {'from': self.ancestor, "value": 0}
                )
            return func(self)
        return wrapper


    @_deploy_without_funds
    def test_deploy_without_funds(self):
        self.ancestor.transfer(self.inheritance_contract.address, self.initial_balance)
        assert self.inheritance_contract.balance() == self.initial_balance

    def test_tranfer_by_non_ancestor(self):
        with reverts():
            self.heirs[0].transfer(self.inheritance_contract.address, self.initial_balance)

    def test_nominal_setup(self):
        self.inheritance_contract.setup(self.heirs[0], 99)
        assert self.inheritance_contract.balance() == self.initial_balance

    def test_not_enough_for_heirs(self):
        self.inheritance_contract.setup(self.heirs[0], 99)
        with reverts():
            self.inheritance_contract.setup(self.heirs[1], 2)
        assert self.inheritance_contract.balance() == self.initial_balance

    def test_too_much_inheritance(self):
        with reverts():
            self.inheritance_contract.setup(self.heirs[0], 101)
        assert self.inheritance_contract.balance() == self.initial_balance
