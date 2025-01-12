from web3 import Web3
import json
from style import style

class Txn_bot():

    def __init__(self, token_address, quantity, slippage, gas_price, swap):
        self.w3 = self.connect()
        self.address, self.private_key = self.set_address()
        self.token_address = Web3.toChecksumAddress(token_address)
        self.token_contract = self.set_token_contract()
        self.utils_address, self.utils = self.set_Utils()
        self.router_address, self.router = self.set_router()
        self.quantity = quantity 
        self.slippage = 1 - (slippage/100)
        self.gas_price = gas_price
        self.SWAP = swap
        self.WBNB = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")

    def connect(self):
        with open("./Settings.json") as f:
            keys = json.load(f)
        w3 = Web3(Web3.HTTPProvider(keys["RPC"]))
        return w3

    def set_address(self):
        with open("./Settings.json") as f:
            keys = json.load(f)
        if len(keys["metamask_address"]) <= 41:
            print(style.RED +"Set your Address in the keys.json file!" + style.RESET)
        if len(keys["metamask_private_key"]) <= 42:
            print(style.RED +"Set your PrivateKey in the keys.json file!"+ style.RESET)
        return(keys["metamask_address"], keys["metamask_private_key"])

    def get_token_decimals(self):
        return self.token_contract.functions.decimals().call()

    def set_Utils(self):
        Utils_address = Web3.toChecksumAddress("0xA7Dd8a34B931D2A0272218Df00D08C3b76A96578") 
        with open("./abis/DEX_Utils.json") as f:
            contract_abi = json.load(f)
        utils = self.w3.eth.contract(address=Utils_address, abi=contract_abi)
        return (Utils_address, utils)

    def getBlockHigh(self):
        return self.w3.eth.block_number

    def set_router(self):
        router_address = Web3.toChecksumAddress("0xA4184bb99692573EF2cae4c00F22b651c75252Fb") 
        with open("./abis/TIGSRouterV1.json") as f:
            contract_abi = json.load(f)
        router = self.w3.eth.contract(address=router_address, abi=contract_abi)
        return (router_address, router)

    def set_token_contract(self):
        with open("./abis/bep20_abi_token.json") as f:
            contract_abi = json.load(f)
        token_contract = self.w3.eth.contract(address=self.token_address, abi=contract_abi)
        return token_contract

    def get_token_balance(self): 
        return self.token_contract.functions.balanceOf(self.address).call() / (10 ** self.token_contract.functions.decimals().call())


    def amountsOut_buy(self):
        Amount = self.utils.functions.getAmountsOut(
            int((self.quantity * (10** 18)) * self.slippage),
            [self.WBNB, self.token_address],
            self.SWAP
            ).call()
        return Amount


    def amountsOut_sell(self):
        Amount = self.utils.functions.getAmountsOut(
            int((self.quantity * (10** self.get_token_decimals())) * self.slippage),
            [self.token_address, self.WBNB],
            self.SWAP
            ).call()
        return Amount


    def get_amounts_out_buy(self):
        Amount = self.utils.functions.getAmountsOut(
            int(self.quantity * self.slippage),
            [self.WBNB, self.token_address],
            self.SWAP
            ).call()
        return Amount


    def get_amounts_out_sell(self):
        Amount = self.utils.functions.getAmountsOut(
            int(self.quantity * self.slippage),
            [self.token_address, self.WBNB],
            self.SWAP
            ).call()
        return Amount


    def buy_token(self):
        self.quantity = self.quantity * (10 ** 18)
        txn = self.router.functions.makeBNBTokenSwap(
            int(self.get_amounts_out_buy()[1]),
            [self.WBNB, self.token_address],
            self.SWAP,
            self.address, 
        ).buildTransaction(
            {'from': self.address, 
            'gas': 480000,
            'gasPrice': self.gas_price,
            'nonce': self.w3.eth.getTransactionCount(self.address), 
            'value': int(self.quantity)}
            )
        signed_txn = self.w3.eth.account.sign_transaction(
            txn,
            self.private_key
        )
        txn = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        print(style.GREEN + "\nTX Hash:",txn.hex() + style.RESET)
        txn_receipt = self.w3.eth.waitForTransactionReceipt(txn)
        if txn_receipt["status"] == 1: return True,style.GREEN +"\nBUY Transaction Successfull!" + style.RESET
        else: return False, style.RED +"\nBUY Transaction Faild!" + style.RESET

    def is_approve(self):
        Approve = self.token_contract.functions.allowance(self.address ,self.router_address).call()
        Aproved_quantity = self.quantity * (10 ** self.token_contract.functions.decimals().call())
        if int(Approve) <= int(Aproved_quantity):
            return False
        else:
            return True

    def approve(self):
        if self.is_approve() == False:
            txn = self.token_contract.functions.approve(
                self.router_address,
                115792089237316195423570985008687907853269984665640564039457584007913129639935 # Max Approve
            ).buildTransaction(
                {'from': self.address, 
                'gas': 100000,
                'gasPrice': self.gas_price,
                'nonce': self.w3.eth.getTransactionCount(self.address), 
                'value': 0}
                )
            signed_txn = self.w3.eth.account.sign_transaction(
                txn,
                self.private_key
            )
            txn = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
            print(style.GREEN + "\nApproved :",txn.hex()+style.RESET)
            txn_receipt = self.w3.eth.waitForTransactionReceipt(txn)   
            if txn_receipt["status"] == 1: return True,style.GREEN +"\nApprove Successfull!"+ style.RESET
            else: return False, style.RED +"\nApprove Transaction Faild!"+ style.RESET
        else:
            return True, style.GREEN +"\nAllready approved!"+ style.RESET


    def sell_token(self):
        #self.quantity = int(self.quantity * (10 ** self.token_contract.functions.decimals().call()))
        txn = self.router.functions.makeTokenBNBSwap(
            int(self.quantity * (10**self.get_token_decimals())),
            int(self.amountsOut_sell()[1]),
            [self.token_address, self.WBNB],
            self.SWAP,
            self.address, 
        ).buildTransaction(
            {'from': self.address, 
            'gas': 550000,
            'gasPrice': self.gas_price,
            'nonce': self.w3.eth.getTransactionCount(self.address), 
            'value': 0}
            )
        signed_txn = self.w3.eth.account.sign_transaction(
            txn,
            self.private_key
        )
        txn = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        print(style.GREEN + "\nSELL TOKENS :",txn.hex() + style.RESET)
        txn_receipt = self.w3.eth.waitForTransactionReceipt(txn)
        if txn_receipt["status"] == 1: return True,style.GREEN +"\nSELL Transaction Successfull!" + style.RESET
        else: return False, style.RED +"\nSELL Transaction Faild!" + style.RESET
        #print(txn_receipt)