from ape import accounts, networks, Contract, project
from ape.types import AddressType
from web3 import Web3
from dotenv import load_dotenv

import json
import os

load_dotenv()

#ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY') or ''
#NODE_URL = f"https://eth-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

#CONTRACT_ADDRESS = "0xA131d02540274992a717C8A3e132b2D6582031eE"

CONTRACT_ABI_PATH = "contract.json"

CALLER = os.getenv('CALLER') or ''
PRIVATE_KEY = os.getenv('PRIVATE_KEY') or ''

# BSC testnet
#CONTRACT_ADDRESS = "0xCB7b3F767D536b7F884f0342372D8dE6E577a1e2"


# opBNB testnet
CONTRACT_ADDRESS = "0xCB7b3F767D536b7F884f0342372D8dE6E577a1e2"
NODE_URL = f"https://opbnb-testnet-rpc.bnbchain.org"

def call_contract_mint(to_addr, nft_ipfs):
    w3 = Web3(Web3.HTTPProvider(NODE_URL))

    if w3.is_connected():
        print('connected')

        # Initialize address nonce
        nonce = w3.eth.get_transaction_count(CALLER)

        # Initialize contract ABI and address
        with open(CONTRACT_ABI_PATH, 'r') as f:
            d = json.load(f)
            abi = json.dumps(d)


        # Create smart contract instance
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

        chain_id = w3.eth.chain_id

        call_function = contract.functions.safeMint(to_addr, nft_ipfs).build_transaction({"chainId": chain_id, "from": CALLER, "nonce": nonce})

        signed_tx = w3.eth.account.sign_transaction(call_function, private_key=PRIVATE_KEY)

        send_tx = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        tx_receipt = w3.eth.wait_for_transaction_receipt(send_tx)

        return tx_receipt
    else:
        print('connection failed')

#call_contract_mint('0x76edf74606cF1b3E2FE7C4670544adE6010C3E56', 'ipfs://QmQGSnjkc3Z7wqsdRt1XMyX5apvYLezbA4GdS9hByfXxEN')
