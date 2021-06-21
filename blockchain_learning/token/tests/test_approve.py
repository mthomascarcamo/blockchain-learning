#!/usr/bin/python3
import unittest
import pytest
from brownie import Token, accounts


class TestToken(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.accounts = accounts
        self.token = Token.deploy("Test Token", "TST", 18, 1e21, {'from': self.accounts[0]})

    def test_approve(self):
        self.token.approve(self.accounts[1], 10**19, {'from': self.accounts[0]})
        assert self.token.allowance(self.accounts[0], self.accounts[1]) == 10**19

    def test_initial_approval_is_zero(self):
        for idx in range(5):
            assert self.token.allowance(self.accounts[0], self.accounts[idx]) == 0

    def test_approve(self):
        self.token.approve(self.accounts[1], 10**19, {'from': self.accounts[0]})
        assert self.token.allowance(self.accounts[0], self.accounts[1]) == 10**19


    def test_modify_approve(self):
        self.token.approve(self.accounts[1], 10**19, {'from': self.accounts[0]})
        self.token.approve(self.accounts[1], 12345678, {'from': self.accounts[0]})

        assert self.token.allowance(self.accounts[0], self.accounts[1]) == 12345678


def test_revoke_approve(token, accounts):
    token.approve(accounts[1], 10**19, {'from': accounts[0]})
    token.approve(accounts[1], 0, {'from': accounts[0]})

    assert token.allowance(accounts[0], accounts[1]) == 0


def test_approve_self(token, accounts):
    token.approve(accounts[0], 10**19, {'from': accounts[0]})

    assert token.allowance(accounts[0], accounts[0]) == 10**19


def test_only_affects_target(token, accounts):
    token.approve(accounts[1], 10**19, {'from': accounts[0]})

    assert token.allowance(accounts[1], accounts[0]) == 0


def test_returns_true(token, accounts):
    tx = token.approve(accounts[1], 10**19, {'from': accounts[0]})

    assert tx.return_value is True


def test_approval_event_fires(accounts, token):
    tx = token.approve(accounts[1], 10**19, {'from': accounts[0]})

    assert len(tx.events) == 1
    assert tx.events["Approval"].values() == [accounts[0], accounts[1], 10**19]
